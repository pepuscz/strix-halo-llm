# Operations

## Select a setup

```bash
export STRIX_SYSTEM=strata-qwen-q4xl  # Winning Qwen setup; default when unset
# export STRIX_SYSTEM=vulkan-iq3xxs  # Winning DeepSeek setup
# export STRIX_SYSTEM=rocm-rocmfpx   # DeepSeek comparison baseline
bin/strixctl validate
bin/strixctl install --allow-reboot
bin/strixctl verify
```

Keep the same `STRIX_SYSTEM` selection for later commands. Installing a different setup replaces the shared `strix-halo-inference.service` and retains the other release's immutable artifacts. The installer retires the previous model service names. The initial Qwen build and tensor conversion run on the target host; the controller observes their progress.

## Service controls

```bash
bin/strixctl status
bin/strixctl stop
bin/strixctl start
bin/strixctl verify
```

Stop restores the captured CPU, GPU, and package-power policy. The cooling
dependency returns all three AXB35 fans to firmware-auto. Verify checks API and
runtime identity, context allocation, model representation, cgroup events,
memory headroom, memory PSI, temperatures, cooling state, package-power
readback, kernel errors, and a bounded API request.

For the default, `strix-fan-governor.service` holds fixed level 5 during GPU
work and for 300 seconds afterward, then returns the fans to firmware-auto. A
missing GPU-busy counter, fan-control fault, governor stop, or governor failure
selects fixed level 5. The controller samples sysfs once per second and never
polls the model API.

Set `strix_verify_full_model_hashes=true` for an explicit full model scrub.
Normal operation verifies immutable download markers and byte sizes to avoid
rehashing approximately 100–111 GB on each run.

## Updates and rollback

Persistent model service changes are made through release manifests and roles.
Do not edit the active systemd unit, GRUB drop-in, hardware policy, DKMS files,
or immutable release-directory content manually.

An update requires a new or reviewed immutable manifest, successful lint and
validation, installation, live verification, and benchmark evidence. Rollback
uses the same path: check out a prior repository tag and install its manifest.
Retained release-specific artifacts are reused only after identity checks.
