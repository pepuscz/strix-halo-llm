# Host platform

The recipes require Ubuntu 26.04, AMD GPU PCI ID `1002:1586`, AXB35-02 board, at least 125,000,000 KiB RAM, no swap, and Secure Boot disabled.

| Model | Qualified kernel | Minimum free disk | Effective non-CMA floor |
|---|---|---:|---:|
| Qwen / Strata | `7.0.0-31-generic` | 220 GB | 8 GiB |
| DeepSeek / Vulkan | `7.0.0-29-generic` | 120 GB | 2 GiB |
| DeepSeek / Lucebox | `7.0.0-29-generic` | 120 GB | 4 GiB |

The qualified machine used BIOS `3.10`. Set these options before installation;
the labels and values below match the BOSGAME BIOS menus:

| BIOS menu | BIOS label | Value |
|---|---|---|
| Advanced > GFX Configuration | `iGPU Configuration` | `UMA_SPECIFIED` |
| Advanced > GFX Configuration | `UMA Frame buffer Size` | `1G` |
| Advanced > GFX Configuration | `PCIE Resizable BAR support` | `Enabled` |
| Advanced > GFX Configuration | `Above 4G Decoding` | `Enabled` |
| Advanced > CPU Configuration | `IOMMU(AMD-Vi)` | `Disabled` |
| Advanced > CPU Configuration | `SVM Mode(AMD-V)` | `Disabled` |
| Advanced > CPU Configuration | `Core Performance Boost` | `Enabled` |
| Security > Secure Boot | `Secure Boot` | `Disabled` |

These settings must be configured manually. Ansible verifies Secure Boot but
does not change BIOS options.

The installer manages this GRUB command line:

```text
amd_pstate=active amd_iommu=off amdgpu.gttsize=126976 ttm.pages_limit=32505856 ttm.page_pool_size=32505856
```
