---
title: Go Types
description: Programmatic management of Cozystack resources using Go types
weight: 2
---

## Go Types

Cozystack publishes its Kubernetes resource types as a Go module, enabling management of Cozystack resources from any Go code. The types are available at [pkg.go.dev/github.com/cozystack/cozystack/api/apps/v1alpha1](https://pkg.go.dev/github.com/cozystack/cozystack/api/apps/v1alpha1).

## Installation

Add the dependency to your Go module:

```bash
go get github.com/cozystack/cozystack/api/apps/v1alpha1@{{< version-pin "cozystack_tag" >}}
```

## Use Cases

The Go types are useful for:

- **Building custom automation tools** - Create scripts or applications that programmatically deploy and manage Cozystack resources
- **Integrating with external systems** - Connect Cozystack with your own CI/CD pipelines, monitoring systems, or orchestration tools
- **Validating configurations** - Use the types to validate resource specifications before applying them to the cluster
- **Generating documentation** - Parse and analyze existing Cozystack resources
- **Building dashboards** - Create custom UIs for Cozystack management

## Available Packages

The module contains packages for each resource type, you can explore it for your specific version in [pkg.go.dev/github.com/cozystack/cozystack/api/apps/v1alpha1](https://pkg.go.dev/github.com/cozystack/cozystack/api/apps/v1alpha1)

### Simple Example

For basic usage, importing a specific package is straightforward:

```go
package main

import (
	"fmt"

	"github.com/cozystack/cozystack/api/apps/v1alpha1/vmdisk"
)

func main() {
	// Create a VMDisk source from a named image
	image := vmdisk.SourceImage{Name: "ubuntu"}
	fmt.Printf("Source: %+v\n", image)
}
```

## Complex Example

This example demonstrates creating and marshaling several Cozystack resource types:

```go
package main

import (
	"encoding/json"
	"fmt"

	"github.com/cozystack/cozystack/api/apps/v1alpha1/postgresql"
	"github.com/cozystack/cozystack/api/apps/v1alpha1/vminstance"
	"github.com/cozystack/cozystack/api/apps/v1alpha1/redis"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/api/resource"
)

func main() {
	// Create a PostgreSQL config with users and databases
	pgConfig := postgresql.Config{
		TypeMeta: metav1.TypeMeta{
			APIVersion: "apps.cozystack.io/v1alpha1",
			Kind:       "Postgres",
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      "my-app-db",
			Namespace: "tenant-myapp",
		},
		Spec: postgresql.ConfigSpec{
			Replicas: 3,
			Size:     resource.MustParse("50Gi"),
			Version:  postgresql.Version("v18"),
			Users: map[string]postgresql.User{
				"appuser": {
					Password:   "secretpassword",
					Replication: false,
				},
				"readonly": {
					Password: "readonlypass",
				},
			},
			Databases: map[string]postgresql.Database{
				"myapp": {
					Extensions: []string{"pg_trgm", "uuid-ossp"},
					Roles: postgresql.DatabaseRoles{
						Admin:    []string{"appuser"},
						Readonly: []string{"readonly"},
					},
				},
			},
			Backup: postgresql.Backup{
				Enabled:         true,
				DestinationPath: "s3://mybackups/postgres/",
				EndpointURL:     "http://minio:9000",
				RetentionPolicy: "30d",
				S3AccessKey:     "myaccesskey",
				S3SecretKey:     "mysecretkey",
				Schedule:        "0 2 * * * *",
			},
			Quorum: postgresql.Quorum{
				MinSyncReplicas: 1,
				MaxSyncReplicas: 1,
			},
			Postgresql: postgresql.PostgreSQL{
				Parameters: postgresql.PostgreSQLParameters{
					MaxConnections: 200,
				},
			},
		},
	}

	// Marshal to JSON for kubectl apply
	pgJSON, _ := json.MarshalIndent(pgConfig, "", "  ")
	fmt.Println(string(pgJSON))

	// Create a Redis config
	redisConfig := redis.Config{
		TypeMeta: metav1.TypeMeta{
			APIVersion: "apps.cozystack.io/v1alpha1",
			Kind:       "Redis",
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      "cache",
			Namespace: "tenant-myapp",
		},
		Spec: redis.ConfigSpec{
			Replicas:        2,
			Size:            resource.MustParse("5Gi"),
			Version:         redis.Version("v8"),
			AuthEnabled:     true,
			ResourcesPreset: redis.ResourcesPreset("medium"),
		},
	}

	// Create a VMInstance with disks
	vmConfig := vminstance.Config{
		TypeMeta: metav1.TypeMeta{
			APIVersion: "apps.cozystack.io/v1alpha1",
			Kind:       "VMInstance",
		},
		ObjectMeta: metav1.ObjectMeta{
			Name:      "my-vm",
			Namespace: "tenant-myapp",
		},
		Spec: vminstance.ConfigSpec{
			InstanceType:    "u1.medium",
			InstanceProfile: "ubuntu",
			RunStrategy:     vminstance.RunStrategy("Always"),
			External:        true,
			ExternalMethod:  vminstance.ExternalMethod("PortList"),
			ExternalPorts:   []int{22, 80, 443},
			Resources: vminstance.Resources{
				Cpu:     resource.MustParse("2"),
				Memory:  resource.MustParse("4Gi"),
				Sockets: resource.MustParse("1"),
			},
			Disks: []vminstance.Disk{
				{Bus: "sata", Name: "rootdisk"},
				{Bus: "sata", Name: "datadisk"},
			},
			Subnets: []vminstance.Subnet{
				{Name: "default"},
			},
			SshKeys: []string{
				"ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ...",
			},
			CloudInit: `#cloud-config
packages:
  - nginx`,
		},
	}
}
```

## Deploying Resources

After creating your resource configurations, you can deploy them using:

1. **kubectl** - Marshal to YAML and apply:
   ```go
   yamlData, _ := json.Marshal(yourConfig)
   // Use YAML marshaling library to convert to YAML
   ```

2. **Direct Kubernetes client** - Use client-go:
   ```go
   import (
     "k8s.io/client-go/kubernetes"
     "k8s.io/apimachinery/pkg/runtime"
   )

   scheme := runtime.NewScheme()
   // Register your types with the scheme
   ```

## Additional Resources

- [Go Package Documentation](https://pkg.go.dev/github.com/cozystack/cozystack/api/apps/v1alpha1)
- [Cozystack GitHub Repository](https://github.com/cozystack/cozystack)
- [Kubernetes API Reference](https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.35/)
