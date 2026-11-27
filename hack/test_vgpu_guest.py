import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "static/examples/vgpu-guest/v1/linux"
SCRIPT = ASSETS / "cozystack-vgpu-license.sh"
TOKEN = "client_configuration_token.tok"


class GuestLicense(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="vgpu-guest-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.runtime = self.root / "run/cozystack-vgpu-license"
        self.tokens = self.runtime / "token"
        self.media = self.runtime / "media"
        self.conf = self.root / "etc/nvidia/gridd.conf"
        self.conf.parent.mkdir(parents=True)
        self.media.mkdir(parents=True)
        self.tokens.mkdir()
        self.outside = self.root / "outside"
        self.outside.write_text("DO NOT CHANGE")
        self.default = self.conf.parent / "ClientConfigToken"
        self.default.mkdir()
        (self.default / TOKEN).write_text("SYNTHETIC-BYOL-SENTINEL")
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.log = self.root / "commands"
        stub = f'#!{sys.executable} -I\n' + '''import os, pathlib, sys
root = pathlib.Path(os.environ["COZYSTACK_VGPU_TEST_ROOT"]).resolve()
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with (root / "commands").open("a") as out:
    out.write(name + " " + " ".join(args) + "\\n")
for arg in args:
    if arg == "/dev/null" and name == "awk": continue
    if arg.startswith("/") and not pathlib.Path(arg).is_relative_to(root):
        sys.exit(90)
if os.environ.get("FAIL_COMMAND") == name:
    sys.exit(1)
mode = os.environ.get("MEDIA", "one")
if name == "lsblk":
    if "--nodeps" in args:
        print("8:2" if os.environ.get("STALE_ALIAS") and args[-1].endswith("GPULICENSE") else "8:1")
    else:
        print(str(root / "root-device") + " ROOT")
        print(str(root / "blank-data-device") + " ")
        if mode != "none": print(str(root / "device") + " GPULICENSE")
        if mode == "ambiguous": print(str(root / "other-device") + " GPULICENSE")
elif name == "blkid":
    if "--probe" in args:
        if os.environ.get("PROBE_STATUS"): sys.exit(int(os.environ["PROBE_STATUS"]))
        print("DEVNAME=" + args[-1])
        print("TYPE=ext4" if args[-1].endswith("root-device") else os.environ.get("PROBE_LABEL", "LABEL=GPULICENSE"))
    else:
        if mode == "none": sys.exit(2)
        print(root / "device")
        if mode == "ambiguous": print(root / "other-device")
elif name == "findmnt":
    if "--mountpoint" in args:
        if not (root / "mounted").exists() or os.environ.get("NO_EXACT_MOUNT"): sys.exit(1)
    column = args[args.index("--output") + 1]
    if column == "TARGET":
        print(root / "run")
        if os.environ.get("PREMOUNTED"): print(root / "run/cozystack-vgpu-license/media")
    elif column == "MAJ:MIN":
        print(os.environ.get("MOUNT_IDENTITY", "8:1"))
    elif column == "OPTIONS":
        print(os.environ.get("MOUNT_OPTIONS", "ro,nodev,nosuid,noexec"))
    elif column == "ID":
        print("2" if os.environ.get("SPLIT_STAGE") and args[-1].endswith("/.stage") else "1")
    elif args[-1].endswith("/token"):
        print(os.environ.get("TOKEN_FSTYPE", os.environ.get("FSTYPE", "tmpfs")))
    else:
        print(os.environ.get("FSTYPE", "tmpfs"))
elif name in ("cp", "mv", "chmod", "rm", "od", "awk"):
    if os.environ.get("PARTIAL_COPY") and name == "cp" and args[-2].endswith(".tok"):
        pathlib.Path(args[-1]).write_bytes(b"SYNTHETIC-PARTIAL")
        sys.exit(1)
    os.execv(os.environ["REAL_" + name.upper()], [name] + args)
elif name == "mount":
    (root / "mounted").touch()
elif name == "umount":
    (root / "mounted").unlink()
elif name != "udevadm":
    sys.exit(91)
'''
        commands = ("blkid", "lsblk", "udevadm", "mount", "umount", "findmnt", "systemctl", "service",
                    "cp", "mv", "chmod", "rm", "od", "awk")
        self.env = dict(os.environ, PATH=f"{self.bin}:{os.environ['PATH']}",
                        COZYSTACK_VGPU_TEST_ROOT=str(self.root))
        for name in commands:
            executable = shutil.which(os.environ.get("VGPU_TEST_AWK", "awk") if name == "awk" else name)
            if executable:
                self.env["REAL_" + name.upper()] = executable
            path = self.bin / name
            path.write_text(stub)
            path.chmod(0o755)
        for name in ("device", "other-device", "root-device", "blank-data-device"):
            (self.root / name).touch()
        self.valid_media()

    def valid_media(self, feature="1", token=b"SYNTHETIC-OPAQUE-TOKEN-A\n"):
        (self.media / TOKEN).write_bytes(token)
        (self.media / "gridd.conf").write_text(f"FeatureType={feature}\nClientConfigTokenPath=/ignored\n")

    def run_script(self, ok=True, **env):
        result = subprocess.run(["sh", str(SCRIPT), "--test-root", str(self.root)],
                                env=dict(self.env, **env), capture_output=True, text=True)
        self.assertEqual(result.returncode == 0, ok, result.stderr)
        self.assertNotIn("SYNTHETIC-", result.stdout + result.stderr)
        self.assertEqual(self.outside.read_text(), "DO NOT CHANGE")
        self.assertEqual((self.default / TOKEN).read_text(), "SYNTHETIC-BYOL-SENTINEL")
        if self.log.exists():
            self.assertNotIn("systemctl ", self.log.read_text())
            self.assertNotIn("service ", self.log.read_text())
        return result

    def assert_empty(self):
        self.assertEqual(list(self.tokens.iterdir()), [])

    def test_license_with_blank_data_disk_probes_only_candidate(self):
        self.run_script()
        commands = self.log.read_text()
        self.assertIn("udevadm settle --timeout=10", commands)
        self.assertIn("lsblk --list --noheadings --paths --raw --output NAME,LABEL", commands)
        probes = [line for line in commands.splitlines() if line.startswith("blkid ")]
        self.assertEqual(probes, [f"blkid --probe --output export --match-tag LABEL -- {self.root / 'device'}"])

    def test_probe_status_two_is_failure_not_absence(self):
        (self.tokens / TOKEN).write_bytes(b"SYNTHETIC-STALE")
        self.run_script(ok=False, PROBE_STATUS="2")
        self.assert_empty()

    def test_stale_udev_label_link_is_failure(self):
        alias = self.root / "dev/disk/by-label/GPULICENSE"
        alias.parent.mkdir(parents=True)
        alias.symlink_to(self.root / "missing-device")
        self.run_script(ok=False, MEDIA="none")
        self.assert_empty()

    def test_label_alias_agrees_with_inventory_and_fresh_probe(self):
        alias = self.root / "dev/disk/by-label/GPULICENSE"
        alias.parent.mkdir(parents=True)
        alias.symlink_to(self.root / "device")
        self.run_script()
        for env in ({"STALE_ALIAS": "yes"}, {"PROBE_LABEL": "LABEL=OTHER"}, {"PROBE_STATUS": "8"}):
            with self.subTest(env=env):
                self.run_script(ok=False, **env)
                self.assert_empty()

    def test_complete_discovery_required(self):
        for command in ("udevadm", "lsblk"):
            with self.subTest(command=command):
                (self.tokens / TOKEN).write_bytes(b"SYNTHETIC-STALE")
                self.run_script(ok=False, FAIL_COMMAND=command)
                self.assert_empty()

    def test_first_boot_modes_and_rotation(self):
        self.run_script()
        self.assertEqual((self.tokens / TOKEN).read_bytes(), (self.media / TOKEN).read_bytes())
        self.assertEqual(stat.S_IMODE((self.tokens / TOKEN).stat().st_mode), 0o744)
        self.assertEqual(stat.S_IMODE(self.tokens.stat().st_mode), 0o755)
        self.assertEqual(stat.S_IMODE(self.conf.stat().st_mode), 0o644)
        self.assertEqual(list(self.tokens.iterdir()), [self.tokens / TOKEN])
        self.assertIn("--options ro,nodev,nosuid,noexec", self.log.read_text())
        self.assertEqual(self.log.read_text().count("umount "), 1)
        self.valid_media("4", b"SYNTHETIC-OPAQUE-TOKEN-B")
        self.run_script()
        self.assertEqual((self.tokens / TOKEN).read_bytes(), b"SYNTHETIC-OPAQUE-TOKEN-B")
        self.assertIn("FeatureType=4", self.conf.read_text())
        self.run_script()
        self.assertEqual(self.conf.read_text().count("FeatureType="), 1)

    def test_merge_preserves_vendor_settings(self):
        self.conf.write_text("# FeatureType=9\nEnableUI=TRUE\nFeatureType=9\nFeatureType = 2\nClientConfigTokenPath=/old\nClientConfigTokenPath=/older\nOtherFeatureType=7\n")
        self.run_script()
        self.assertEqual(self.conf.read_text(), f"# FeatureType=9\nEnableUI=TRUE\nOtherFeatureType=7\nClientConfigTokenPath={self.tokens}\nFeatureType=1\n")

    def test_no_media_succeeds_with_empty_managed_path(self):
        self.conf.write_text("FeatureType=4\nClientConfigTokenPath=/stale\n")
        (self.tokens / TOKEN).write_text("SYNTHETIC-STALE")
        self.run_script(MEDIA="none")
        self.assert_empty()
        self.assertIn(f"ClientConfigTokenPath={self.tokens}", self.conf.read_text())
        self.assertIn("FeatureType=4", self.conf.read_text())
        self.assertNotIn("mount ", self.log.read_text())
        self.assertNotIn("blkid ", self.log.read_text())

    def test_missing_runtime_and_config(self):
        shutil.rmtree(self.runtime)
        self.run_script(MEDIA="none")
        self.assert_empty()
        self.assertEqual(self.conf.read_text(), f"ClientConfigTokenPath={self.tokens}\n")

    def test_invalid_media_fails_after_stale_cleanup(self):
        variants = ("missing", "empty", "directory", "symlink", "config-missing", "config-symlink",
                    "fifo", "config-fifo", "feature-missing", "feature-invalid", "feature-newline", "feature-duplicate", "feature-command")
        for variant in variants:
            with self.subTest(variant=variant):
                for item in self.media.iterdir():
                    if item.is_dir(): item.rmdir()
                    else: item.unlink()
                self.valid_media()
                token = self.media / TOKEN
                conf = self.media / "gridd.conf"
                if variant in ("missing", "empty", "directory", "symlink", "fifo"):
                    token.unlink()
                    if variant == "empty": token.touch()
                    if variant == "directory": token.mkdir()
                    if variant == "symlink": token.symlink_to(self.outside)
                    if variant == "fifo": os.mkfifo(token)
                elif variant == "config-fifo":
                    conf.unlink()
                    os.mkfifo(conf)
                elif variant == "config-missing": conf.unlink()
                elif variant == "config-symlink":
                    conf.unlink()
                    conf.symlink_to(self.outside)
                else:
                    conf.write_text({"feature-missing": "Other=1\n", "feature-invalid": "FeatureType=2\n",
                                     "feature-newline": "FeatureType=\n1\n",
                                     "feature-duplicate": "FeatureType=1\nFeatureType=4\n",
                                     "feature-command": "FeatureType=$(touch /outside)\n"}[variant])
                (self.tokens / TOKEN).write_text("SYNTHETIC-STALE")
                self.run_script(ok=False)
                self.assert_empty()
                self.assertIn(f"ClientConfigTokenPath={self.tokens}", self.conf.read_text())

    def test_ambiguity_mount_failure_and_foreign_mount(self):
        for env in ({"MEDIA": "ambiguous"}, {"FAIL_COMMAND": "mount"}, {"PREMOUNTED": "yes"}):
            with self.subTest(env=env):
                self.log.write_text("")
                self.run_script(ok=False, **env)
                self.assert_empty()
                self.assertNotIn("umount ", self.log.read_text())

    def test_unmount_failure_is_failure_and_removes_token(self):
        self.run_script(ok=False, FAIL_COMMAND="umount")
        self.assert_empty()

    def test_memory_filesystem_required_before_token_write(self):
        self.run_script(ok=False, FSTYPE="ext4")
        self.assert_empty()
        self.assertFalse(self.conf.exists())
        self.assertNotIn("mount ", self.log.read_text())

    def test_token_child_mount_must_also_be_memory_backed(self):
        self.run_script(ok=False, TOKEN_FSTYPE="ext4")
        self.assert_empty()
        self.assertNotIn("mount ", self.log.read_text())

    def test_runtime_symlink_and_unowned_subdirectory_rejected(self):
        self.tokens.rmdir()
        self.tokens.symlink_to(self.default)
        self.run_script(ok=False)
        self.tokens.unlink()
        self.tokens.mkdir()
        (self.tokens / "foreign-directory").mkdir()
        self.run_script(ok=False)
        self.assertTrue((self.tokens / "foreign-directory").is_dir())

    @unittest.skipIf(os.geteuid() == 0, "Permission failures require an unprivileged test process")
    def test_token_read_and_copy_failures_leave_no_token(self):
        (self.media / TOKEN).chmod(0)
        try:
            self.run_script(ok=False)
            self.assert_empty()
        finally:
            (self.media / TOKEN).chmod(0o644)
        self.tokens.chmod(0o555)
        try:
            self.run_script(ok=False)
            self.assert_empty()
        finally:
            self.tokens.chmod(0o755)

    def test_discovery_and_filesystem_probe_errors_are_not_no_media(self):
        for command in ("blkid", "findmnt"):
            with self.subTest(command=command):
                self.run_script(ok=False, FAIL_COMMAND=command)
                self.assert_empty()

    def test_posix_shell_without_guest_python(self):
        self.assertEqual(SCRIPT.read_text().splitlines()[0], "#!/bin/sh")
        self.assertNotIn("python", SCRIPT.read_text().lower())

    def test_local_utf8_comments_crlf_and_missing_final_newline(self):
        original = "# Mémoire — 設定\r\nVendor=✓\r\nFeatureTypeExtra=7"
        self.conf.write_bytes(original.encode())
        self.run_script()
        self.assertTrue(self.conf.read_bytes().startswith(original.encode() + b"\n"))

    def test_local_config_rejects_binary_and_bare_carriage_returns(self):
        for content in (b"Vendor=\x00\n", b"Vendor=yes\rBAD\n", b"Vendor=yes\r"):
            with self.subTest(content=content):
                self.conf.write_bytes(content)
                self.run_script(ok=False)
                self.assert_empty()
                self.assertEqual(self.conf.read_bytes(), content)

    def test_opaque_binary_token_and_media_crlf(self):
        data = bytes(range(256)) + b"\x00\n\xff"
        self.valid_media(token=data)
        (self.media / "gridd.conf").write_bytes(b"# generated\r\n\tFeatureType \t= 4\t\r\n")
        self.run_script()
        self.assertEqual((self.tokens / TOKEN).read_bytes(), data)
        self.assertIn("FeatureType=4\n", self.conf.read_text())

    def test_malformed_text_and_identical_feature_duplicates_fail(self):
        for content in (b"FeatureType=1\nFeatureType=1\n", b"FeatureType=1\x00\n",
                        b"FeatureType=1 4\n", b"FeatureType=1 # comment\n", b"FeatureType=1\rjunk\n",
                        b"#\xff\nFeatureType=1\n"):
            with self.subTest(content=content):
                (self.media / "gridd.conf").write_bytes(content)
                self.run_script(ok=False)
                self.assert_empty()

    def test_staging_must_share_token_mount_and_effective_readonly_options(self):
        for env in ({"SPLIT_STAGE": "yes"}, {"MOUNT_OPTIONS": "rw,nodev,nosuid,noexec"}):
            with self.subTest(env=env):
                self.run_script(ok=False, **env)
                self.assert_empty()

    def test_exact_mountpoint_and_candidate_identity_required(self):
        for env in ({"NO_EXACT_MOUNT": "yes"}, {"MOUNT_IDENTITY": "8:2"}):
            with self.subTest(env=env):
                self.log.write_text("")
                self.run_script(ok=False, **env)
                self.assert_empty()
                self.assertIn("umount ", self.log.read_text())

    def test_external_utility_failures_leave_no_published_token(self):
        for command in ("cp", "mv", "chmod", "od", "awk"):
            with self.subTest(command=command):
                self.run_script(ok=False, FAIL_COMMAND=command)
                self.assert_empty()
        self.run_script(ok=False, PARTIAL_COPY="yes")
        self.assert_empty()

    def test_hardlinked_token_and_config_are_rejected(self):
        os.link(self.media / TOKEN, self.root / "linked-token")
        self.run_script(ok=False)
        self.assert_empty()

    def test_hidden_stale_files_removed_but_directories_preserved(self):
        (self.tokens / ".old").write_bytes(b"SYNTHETIC-STALE")
        self.run_script(MEDIA="none")
        self.assert_empty()
        (self.tokens / ".unexpected").mkdir()
        self.run_script(ok=False)
        self.assertTrue((self.tokens / ".unexpected").is_dir())

    def test_interrupted_staging_is_cleaned_before_reuse(self):
        stage = self.runtime / ".stage"
        stage.mkdir(mode=0o700)
        (stage / "token").write_bytes(b"SYNTHETIC-PARTIAL")
        conf_stage = self.conf.parent / ".cozystack-vgpu-license"
        conf_stage.mkdir(mode=0o700)
        (conf_stage / "config").write_bytes(b"FeatureType=bad\n")
        self.run_script()
        self.assertFalse(stage.exists())
        self.assertFalse(conf_stage.exists())
        self.assertEqual((self.tokens / TOKEN).read_bytes(), (self.media / TOKEN).read_bytes())

    def test_unsafe_staging_and_configuration_leave_no_token(self):
        cases = ("stage-symlink", "stage-permissions", "stage-directory", "stage-unknown",
                 "config-hardlink", "config-writable", "parent-symlink")
        for case in cases:
            with self.subTest(case=case):
                self.conf.unlink(missing_ok=True)
                stage = self.runtime / ".stage"
                if stage.is_symlink(): stage.unlink()
                elif stage.exists(): shutil.rmtree(stage)
                if case == "stage-symlink": stage.symlink_to(self.default)
                elif case.startswith("stage-"):
                    stage.mkdir(mode=0o700)
                    if case == "stage-permissions": stage.chmod(0o755)
                    if case == "stage-directory": (stage / "token").mkdir()
                    if case == "stage-unknown": (stage / "unexpected").touch()
                elif case == "config-hardlink": os.link(self.outside, self.conf)
                elif case == "config-writable":
                    self.conf.write_bytes(b"FeatureType=1\n")
                    self.conf.chmod(0o666)
                elif case == "parent-symlink":
                    self.conf.parent.rename(self.root / "nvidia-real")
                    self.conf.parent.symlink_to(self.root / "nvidia-real")
                self.run_script(ok=False)
                self.assert_empty()

    def test_unrelated_config_mode_is_not_widened(self):
        self.conf.write_text("VendorSetting=yes\n")
        self.conf.chmod(0o600)
        self.run_script()
        self.assertEqual(stat.S_IMODE(self.conf.stat().st_mode), 0o600)
        self.assertIn("VendorSetting=yes", self.conf.read_text())

    def test_config_symlink_rejected(self):
        self.conf.symlink_to(self.outside)
        self.run_script(ok=False)

    def test_workflow_runs_both_lanes_and_windows_engines(self):
        workflow = (ROOT / ".github/workflows/vgpu-guest.yml").read_text()
        linux = workflow.split("\n  linux:\n", 1)[1].split("\n  windows:\n", 1)[0]
        windows = workflow.split("\n  windows:\n", 1)[1]
        self.assertIn("python3 -I hack/test_vgpu_guest.py", linux)
        self.assertIn("shell: [powershell, pwsh]", windows)
        self.assertIn("shell: ${{ matrix.shell }}", windows)
        self.assertIn("$config.Run.Path = './hack/Test-VgpuGuest.Tests.ps1'", windows)
        self.assertIn("$config.Run.Throw = $true", windows)
        self.assertIn("$result.TotalCount -eq 0", windows)
        for lane in (linux, windows):
            self.assertIn("fail-fast: false", lane)
        for path in ("static/examples/vgpu-guest/**", "hack/test_vgpu_guest.py",
                     "hack/Test-VgpuGuest.Tests.ps1", ".github/workflows/vgpu-guest.yml"):
            self.assertEqual(workflow.count(f"      - '{path}'"), 2, path)

    def test_empty_test_selection_is_not_success(self):
        result = subprocess.run([sys.executable, "-I", __file__, "-k", "NO_MATCHING_VGPU_TEST"],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_test_root_must_be_explicit_and_match_environment(self):
        result = subprocess.run(["sh", str(SCRIPT), "--test-root", "/"],
                                env=self.env, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.log.exists())

    def test_client_only_dependency_not_boot_target(self):
        unit = (ASSETS / "cozystack-vgpu-license.service").read_text()
        dropin = (ASSETS / "nvidia-gridd.service.d/cozystack-vgpu-license.conf").read_text()
        self.assertIn("Type=oneshot", unit)
        self.assertNotIn("RemainAfterExit=", unit)
        self.assertIn("Before=nvidia-gridd.service", unit)
        self.assertIn("ExecStart=/usr/local/sbin/cozystack-vgpu-license", unit)
        self.assertIn("Requires=cozystack-vgpu-license.service", dropin)
        self.assertIn("After=cozystack-vgpu-license.service", dropin)
        self.assertNotIn("WantedBy=", unit)
        self.assertNotIn("RequiredBy=", unit)
        self.assertNotIn("FailureAction=", unit)
        self.assertNotIn("OnFailure=", unit)


@unittest.skipUnless(sys.platform.startswith("linux"), "Requires Linux util-linux and e2fsprogs; no mounts or block devices")
class LinuxProbeFormat(unittest.TestCase):
    def test_export_tag_filter_still_includes_device_name(self):
        for tool in ("mkfs.ext4", "blkid"):
            self.assertIsNotNone(shutil.which(tool), f"Linux CI prerequisite missing: {tool}")
        with tempfile.TemporaryDirectory(prefix="vgpu-probe-") as temporary:
            image = Path(temporary) / "synthetic-license.img"
            image.write_bytes(bytes(4 * 1024 * 1024))
            subprocess.run(["mkfs.ext4", "-F", "-L", "GPULICENSE", str(image)],
                           check=True, capture_output=True)
            result = subprocess.run(["blkid", "--probe", "--output", "export", "--match-tag", "LABEL", "--", str(image)],
                                    check=True, capture_output=True, text=True)
            self.assertEqual(result.stdout, f"DEVNAME={image}\nLABEL=GPULICENSE\n")


if __name__ == "__main__":
    unittest.main()
