#!/bin/sh
set +x
umask 077
LC_ALL=C
export LC_ALL
root=
if [ "$#" != 0 ]; then
    if [ "$#" != 2 ] || [ "$1" != --test-root ] || [ "$2" != "${COZYSTACK_VGPU_TEST_ROOT:-}" ]; then
        echo 'Invalid sandbox invocation' >&2
        exit 1
    fi
    case "$2" in
        /|*..*|*[!A-Za-z0-9_./-]*|'') echo 'Invalid sandbox invocation' >&2; exit 1 ;;
        /*) root=$2 ;;
        *) echo 'Invalid sandbox invocation' >&2; exit 1 ;;
    esac
    [ -d "$root" ] && [ ! -L "$root" ] || exit 1
else
    PATH=/usr/sbin:/usr/bin:/sbin:/bin
    export PATH
fi
uid=$(id -u) || exit 1
if [ -z "$root" ] && [ "$uid" != 0 ]; then
    echo 'Root is required' >&2
    exit 1
fi
runtime=$root/run/cozystack-vgpu-license
tokens=$runtime/token
media=$runtime/media
stage=$runtime/.stage
config=$root/etc/nvidia/gridd.conf
config_stage=$root/etc/nvidia/.cozystack-vgpu-license
label_link=$root/dev/disk/by-label/GPULICENSE
mounted=false
cleanup_ready=false
stage_ready=false
config_stage_ready=false

fail() {
    echo "$1" >&2
    exit 1
}

directory() {
    if [ "$1" != "$root" ] && [ "$1" != / ]; then
        case "${1%/*}" in
            '') directory / 0755 || return 1 ;;
            *) directory "${1%/*}" 0755 || return 1 ;;
        esac
    fi
    if [ ! -e "$1" ] && [ ! -L "$1" ]; then
        mkdir -m "$2" "$1" 2>/dev/null || return 1
    fi
    found=$(find "$1" -prune -type d -user "$uid" ! -perm -0020 ! -perm -0002 -print 2>/dev/null) || return 1
    [ "$found" = "$1" ] || return 1
    if [ "$2" = 0700 ]; then
        found=$(find "$1" -prune -perm 0700 -print 2>/dev/null) || return 1
        [ "$found" = "$1" ] || return 1
    fi
}

regular() {
    found=$(find "$1" -prune -type f -links 1 -print 2>/dev/null) || return 1
    [ "$found" = "$1" ]
}

trusted_file() {
    regular "$1" || return 1
    found=$(find "$1" -prune -user "$uid" ! -perm -0020 ! -perm -0002 -print 2>/dev/null) || return 1
    [ "$found" = "$1" ]
}

mount_id() {
    identity=$(findmnt --noheadings --raw --output ID --target "$1" 2>/dev/null) || return 1
    case "$identity" in ''|*[!0-9]*) return 1 ;; esac
    printf '%s\n' "$identity"
}

clear_tokens() {
    token_mount=$(mount_id "$tokens") || return 1
    for entry in "$tokens"/* "$tokens"/.[!.]* "$tokens"/..?*; do
        [ -e "$entry" ] || [ -L "$entry" ] || continue
        if [ ! -L "$entry" ]; then
            [ ! -d "$entry" ] || return 1
            entry_mount=$(mount_id "$entry") || return 1
            [ "$entry_mount" = "$token_mount" ] || return 1
        fi
    done
    for entry in "$tokens"/* "$tokens"/.[!.]* "$tokens"/..?*; do
        [ -e "$entry" ] || [ -L "$entry" ] || continue
        rm "$entry" 2>/dev/null || return 1
    done
}

clear_stage() {
    parent_mount=$(mount_id "$1") || return 1
    for entry in "$1"/* "$1"/.[!.]* "$1"/..?*; do
        [ -e "$entry" ] || [ -L "$entry" ] || continue
        case "${entry##*/}" in
            token|config|bytes|inventory) ;;
            *) return 1 ;;
        esac
        regular "$entry" || return 1
        entry_mount=$(mount_id "$entry") || return 1
        [ "$entry_mount" = "$parent_mount" ] || return 1
    done
    for entry in "$1"/token "$1"/config "$1"/bytes "$1"/inventory; do
        [ -e "$entry" ] || continue
        rm "$entry" 2>/dev/null || return 1
    done
}

finish() {
    status=$?
    trap - 0
    if "$mounted"; then
        if ! umount -- "$media" >/dev/null 2>&1; then
            echo 'vGPU license media unmount failed' >&2
            status=1
        fi
    fi
    if "$stage_ready"; then
        if ! clear_stage "$stage" || ! rmdir "$stage" 2>/dev/null; then
            echo 'vGPU token staging cleanup failed' >&2
            status=1
        fi
    fi
    if "$config_stage_ready"; then
        if ! clear_stage "$config_stage" || ! rmdir "$config_stage" 2>/dev/null; then
            echo 'vGPU config staging cleanup failed' >&2
            status=1
        fi
    fi
    if [ "$status" != 0 ] && "$cleanup_ready"; then
        clear_tokens || echo 'vGPU managed token cleanup failed' >&2
    fi
    exit "$status"
}
trap finish 0
trap 'exit 1' HUP INT TERM

text_file() {
    od -A n -v -t u1 "$1" > "$config_stage/bytes" 2>/dev/null || return 1
    awk -v ascii="$2" '
        { for (i = 1; i <= NF; i++) {
            if (($i < 32 && $i != 9 && $i != 10 && $i != 13) || $i == 127 || (ascii && $i > 126)) bad = 1
            if (previous == 13 && $i != 10) bad = 1
            previous = $i
        } }
        END { exit (bad || previous == 13) }
    ' "$config_stage/bytes" 2>/dev/null
}

merge_config() {
    source=/dev/null
    if [ -e "$config" ] || [ -L "$config" ]; then
        trusted_file "$config" || return 1
        text_file "$config" 0 || return 1
        source=$config
        cp -p "$config" "$config_stage/config" 2>/dev/null || return 1
    else
        : > "$config_stage/config" || return 1
        chmod 0644 "$config_stage/config" 2>/dev/null || return 1
    fi
    awk -v path="$tokens" -v feature="$1" '
        /^[ \t]*ClientConfigTokenPath[ \t]*=/ { next }
        feature != "" && /^[ \t]*FeatureType[ \t]*=/ { next }
        { print }
        END {
            print "ClientConfigTokenPath=" path
            if (feature != "") print "FeatureType=" feature
        }
    ' "$source" > "$config_stage/config" 2>/dev/null || return 1
    trusted_file "$config_stage/config" || return 1
    if [ -e "$config" ] || [ -L "$config" ]; then
        trusted_file "$config" || return 1
    fi
    mv "$config_stage/config" "$config" 2>/dev/null
}

block_device() {
    if [ -n "$root" ]; then
        case "$1" in "$root"/*) [ -f "$1" ] ;; *) return 1 ;; esac
    else
        [ -b "$1" ]
    fi
}

for path in "$runtime" "$tokens" "$media"; do
    directory "$path" 0755 || fail 'Unsafe vGPU runtime directory'
done
cleanup_ready=true
mounts=$(findmnt --kernel --list --noheadings --raw --output TARGET 2>/dev/null) || fail 'vGPU mount inventory failed'
newline='
'
for path in "$media" "$stage" "$config_stage"; do
    case "$newline$mounts$newline" in *"$newline$path$newline"*) fail 'vGPU mountpoint is already in use' ;; esac
done
clear_tokens || fail 'vGPU managed token cleanup failed'
for path in "$tokens" "$runtime"; do
    filesystem=$(findmnt --noheadings --raw --output FSTYPE --target "$path" 2>/dev/null) || fail 'vGPU filesystem discovery failed'
    case "$filesystem" in tmpfs|ramfs) ;; *) fail 'vGPU token directory requires a memory filesystem' ;; esac
done
directory "$stage" 0700 || fail 'Unsafe vGPU token staging directory'
stage_ready=true
stage_mount=$(mount_id "$stage") || fail 'vGPU token staging discovery failed'
token_mount=$(mount_id "$tokens") || fail 'vGPU token filesystem discovery failed'
[ "$stage_mount" = "$token_mount" ] || fail 'vGPU token staging must share the token mount'
clear_stage "$stage" || fail 'Unsafe vGPU token staging contents'
directory "$config_stage" 0700 || fail 'Unsafe vGPU configuration directory'
config_stage_ready=true
config_mount=$(mount_id "${config%/*}") || fail 'vGPU config mount discovery failed'
staging_mount=$(mount_id "$config_stage") || fail 'vGPU config staging discovery failed'
[ "$config_mount" = "$staging_mount" ] || fail 'vGPU config staging must share the config mount'
clear_stage "$config_stage" || fail 'Unsafe vGPU configuration staging contents'
merge_config '' || fail 'vGPU license configuration preparation failed'

udevadm settle --timeout=10 >/dev/null 2>&1 || fail 'vGPU device discovery did not settle'
lsblk --list --noheadings --paths --raw --output NAME,LABEL > "$stage/inventory" 2>/dev/null || fail 'vGPU block inventory failed'
device=$(awk '
    NF > 2 || $1 !~ /^\// { bad = 1 }
    $2 == "GPULICENSE" { count++; device = $1 }
    END { if (bad || count > 1) exit 1; if (count == 1) print device }
' "$stage/inventory" 2>/dev/null) || fail 'Ambiguous or invalid vGPU license inventory'
if [ -e "$label_link" ] || [ -L "$label_link" ]; then
    block_device "$label_link" || fail 'Stale vGPU license label link'
    [ -n "$device" ] || fail 'vGPU license label missing from inventory'
    link_id=$(lsblk --nodeps --noheadings --output MAJ:MIN -- "$label_link" 2>/dev/null) || fail 'vGPU label identity discovery failed'
    device_id=$(lsblk --nodeps --noheadings --output MAJ:MIN -- "$device" 2>/dev/null) || fail 'vGPU device identity discovery failed'
    [ -n "$link_id" ] || fail 'vGPU license label identity mismatch'
    [ "$link_id" = "$device_id" ] || fail 'vGPU license label identity mismatch'
fi
[ -n "$device" ] || exit 0
case "$device" in *[!A-Za-z0-9_./-]*) fail 'Unsupported vGPU license device path' ;; esac
block_device "$device" || fail 'vGPU license candidate is not a block device'
label=$(blkid --probe --output export --match-tag LABEL -- "$device" 2>/dev/null) || fail 'vGPU license media probe failed'
[ "$label" = "DEVNAME=$device${newline}LABEL=GPULICENSE" ] || fail 'vGPU license candidate label mismatch'
mount --options ro,nodev,nosuid,noexec -- "$device" "$media" >/dev/null 2>&1 || fail 'vGPU license media mount failed'
mounted=true
device_id=$(lsblk --nodeps --noheadings --raw --output MAJ:MIN -- "$device" 2>/dev/null) || fail 'vGPU device identity discovery failed'
mounted_id=$(findmnt --noheadings --raw --output MAJ:MIN --mountpoint "$media" 2>/dev/null) || fail 'vGPU license mount verification failed'
[ -n "$device_id" ] || fail 'vGPU license mount source mismatch'
[ "$device_id" = "$mounted_id" ] || fail 'vGPU license mount source mismatch'
options=$(findmnt --noheadings --raw --output OPTIONS --mountpoint "$media" 2>/dev/null) || fail 'vGPU license mount verification failed'
for option in ro nodev nosuid noexec; do
    case ",$options," in *",$option,"*) ;; *) fail 'Unsafe vGPU license mount options' ;; esac
done
regular "$media/client_configuration_token.tok" || fail 'Invalid vGPU license token file'
[ -s "$media/client_configuration_token.tok" ] || fail 'Invalid vGPU license token file'
regular "$media/gridd.conf" || fail 'Invalid vGPU license media configuration'
text_file "$media/gridd.conf" 1 || fail 'Invalid vGPU license media configuration'
feature=$(awk '
    { sub(/\r$/, ""); if ($0 ~ /\r/) bad = 1 }
    /^[ \t]*FeatureType[ \t]*=/ {
        count++; sub(/^[ \t]*FeatureType[ \t]*=[ \t]*/, ""); sub(/[ \t]*$/, "")
        if ($0 != "1" && $0 != "4") bad = 1
        feature = $0
    }
    END { if (bad || count != 1) exit 1; print feature }
' "$media/gridd.conf" 2>/dev/null) || fail 'Invalid vGPU license FeatureType'
cp "$media/client_configuration_token.tok" "$stage/token" 2>/dev/null || fail 'vGPU license token copy failed'
regular "$stage/token" || fail 'Invalid staged vGPU token'
[ -s "$stage/token" ] || fail 'Invalid staged vGPU token'
chmod 0744 "$stage/token" 2>/dev/null || fail 'vGPU license token mode failed'
merge_config "$feature" || fail 'vGPU license configuration merge failed'
[ ! -e "$tokens/client_configuration_token.tok" ] || fail 'Unexpected vGPU token destination'
[ ! -L "$tokens/client_configuration_token.tok" ] || fail 'Unexpected vGPU token destination'
mv "$stage/token" "$tokens/client_configuration_token.tok" 2>/dev/null || fail 'vGPU license token installation failed'
