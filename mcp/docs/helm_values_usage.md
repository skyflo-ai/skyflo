# Helm Values File Support

This document explains how to use the Helm values file generation and installation with values features of Skyflo.ai.

## Overview

Skyflo.ai now supports:
1. Generating YAML values files for Helm charts
2. Installing Helm charts with custom values from those files

## Generate Helm Values File

The `generate_helm_values` tool allows you to create a YAML values file for your Helm chart:

```python
# Generate a values file with custom configuration
values_file_path = generate_helm_values(
    values={
        "service": {
            "type": "ClusterIP",
            "port": 80
        },
        "replicaCount": 3,
        "image": {
            "repository": "nginx",
            "tag": "latest",
            "pullPolicy": "IfNotPresent"
        }
    },
    output_path="/path/to/save/values.yaml"  # Optional - if not provided, a temporary file is created
)
```

If `output_path` is not provided, the function will create a temporary file and return its path.

## Install Helm Chart with Custom Values

The `helm_install_with_values` tool allows you to install a Helm chart with custom values:

```python
# Install a chart with custom values
result = helm_install_with_values(
    name="my-release",
    chart="stable/nginx",
    version="1.2.3",
    values={
        "service": {
            "type": "ClusterIP",
            "port": 80
        },
        "replicaCount": 3,
        "image": {
            "repository": "nginx",
            "tag": "latest",
            "pullPolicy": "IfNotPresent"
        }
    },
    namespace="my-namespace"  # Optional
)
```

This will:
1. Generate a temporary values file with your custom configuration
2. Install the chart using that values file
3. Clean up the temporary file when done

## Example Usage in Natural Language

Here are examples of how you can use these features through natural language:

### Generate Values File
"Generate a Helm values file that sets nginx replicas to 3 and service port to 80"

### Install with Values
"Install nginx chart version 1.2.3 with 3 replicas and LoadBalancer service type"

## Notes

- The values file is automatically cleaned up after installation when using `helm_install_with_values`
- When generating a values file with `generate_helm_values`, you're responsible for cleaning up the file if a specific path is provided
- If no `output_path` is provided to `generate_helm_values`, it creates a temporary file that will be automatically removed when your system cleans up temp files 