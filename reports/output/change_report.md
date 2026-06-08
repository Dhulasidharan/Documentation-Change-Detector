# Documentation Change Report

Comparing **v25.0.0** -> **v26.3.0**

- Old: https://r2.nodejs.org/dist/v25.0.0/docs/api/permissions.html  
  captured 2026-06-08T11:25:05.186887+00:00
- New: https://nodejs.org/docs/latest/api/permissions.html  
  captured 2026-06-08T11:25:07.354815+00:00

## Summary

| Change | Count |
| --- | ---: |
| Sections added | 3 |
| Sections removed | 0 |
| Sections modified | 3 |
| Sections unchanged | 6 |
| API signatures added | 2 |
| API signatures removed | 0 |

## API Signature Changes

### Added

- `permission.drop(scope[, reference])`
- `process._debugProcess()`

## Added Sections

### + Configuration file support  `#permissions_configuration_file_support`

> Configuration file support In addition to passing permission flags on the command line, they can also be declared in a Node.js configuration file when using the experimental [--experimental-config-fil...

### + process._debugProcess() and cross-process Inspector activation  `#permissions_process_debugprocess_and_cross_process_inspector_activation`

> process._debugProcess() and cross-process Inspector activation The kInspector permission scope restricts the current process from opening its own V8 Inspector. However, process._debugProcess(pid) — wh...

### + permission.drop(scope[, reference])  `#permissions_permission_drop_scope_reference`

> permission.drop(scope[, reference]) API call to drop permissions at runtime. This operation is irreversible. When called without a reference, the entire scope is dropped. When called with a reference,...

## Modified Sections

### ~ Runtime API  `#permissions_runtime_api`

Similarity: 96.32%

```diff
--- old::Runtime API
+++ new::Runtime API
@@ -1,2 +1,2 @@
 Runtime API
-When enabling the Permission Model through the --permission flag a new property permission is added to the process object. This property contains one function:
+When enabling the Permission Model through the --permission flag a new property permission is added to the process object. This property contains the following functions:
```

### ~ Permission Model constraints  `#permissions_permission_model_constraints`

Similarity: 99.80%

```diff
--- old::Permission Model constraints
+++ new::Permission Model constraints
@@ -1,3 +1,3 @@
 Permission Model constraints
 There are constraints you need to know before using this system:
-The model does not inherit to a worker thread. When using the Permission Model the following features will be restricted: Native modules Network Child process Worker Threads Inspector protocol File system access WASI The Permission Model is initialized after the Node.js environment is set up. However, certain flags such as --env-file or --openssl-config are designed to read files before environment initialization. As a result, such flags are not subject to the rules of the Permission Model. The same applies for V8 flags that can be set via runtime through v8.setFlagsFromString. OpenSSL engines cannot be requested at runtime when the Permission Model is enabled, affecting the built-in crypto, https, and tls modules. Run-Time Loadable Extensions cannot be loaded when the Permission Model is enabled, affecting the sqlite module. Using existing file descriptors via the node:fs module bypasses the Permission Model.
+The model does not inherit to a worker thread. When using the Permission Model the following features will be restricted: Native modules Network Child process Worker Threads Inspector protocol File system access WASI FFI The Permission Model is initialized after the Node.js environment is set up. However, certain flags such as --env-file or --openssl-config are designed to read files before environment initialization. As a result, such flags are not subject to the rules of the Permission Model. The same applies for V8 flags that can be set via runtime through v8.setFlagsFromString. OpenSSL engines cannot be requested at runtime when the Permission Model is enabled, affecting the built-in crypto, https, and tls modules. Run-Time Loadable Extensions cannot be loaded when the Permission Model is enabled, affecting the sqlite module. Using existing file descriptors via the node:fs module bypasses the Permission Model.
```

### ~ Permission Model  `#permissions_permission_model`

Similarity: 92.15%

```diff
--- old::Permission Model
+++ new::Permission Model
@@ -1,8 +1,9 @@
 Permission Model
-VersionChanges v23.5.0, v22.13.0 This feature is no longer experimental. v20.0.0 Added in: v20.0.0
+VersionChangesv23.5.0, v22.13.0This feature is no longer experimental.
+Stability: 2 - Stable
 The Node.js Permission Model is a mechanism for restricting access to specific resources during execution. The API exists behind a flag --permission which when enabled, will restrict access to all available permissions.
 The available permissions are documented by the --permission flag.
-When starting Node.js with --permission, the ability to access the file system through the fs module, access the network, spawn processes, use node:worker_threads, use native addons, use WASI, and enable the runtime inspector will be restricted (the listener for SIGUSR1 won't be created).
+When starting Node.js with --permission, the ability to access the file system through the fs module, access the network, spawn processes, use node:worker_threads, use native addons, use WASI, use FFI, and enable the runtime inspector will be restricted (the listener for SIGUSR1 won't be created).
 $ node --permission index.js
 
 Error: Access to this API has been restricted
@@ -12,4 +13,4 @@
   resource: '/home/user/index.js'
 }
 Allowing access to spawning a process and creating worker threads can be done using the --allow-child-process and --allow-worker respectively.
-To allow network access, use --allow-net and for allowing native addons when using permission model, use the --allow-addons flag. For WASI, use the --allow-wasi flag.
+To allow network access, use --allow-net and for allowing native addons when using permission model, use the --allow-addons flag. For WASI, use the --allow-wasi flag. For FFI, use the --allow-ffi flag. The node:ffi module also requires the --experimental-ffi flag and is only available in builds with FFI support.
```

