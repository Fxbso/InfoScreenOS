# VirtualBox test edition

This is a **Debian 13 Trixie Live ISO**, with the same InfoScreen backend/dashboard/renderer as the Raspberry Pi package, but using Xorg/SDL2 in the VM (no Chromium). This edition is designed to boot directly from the ISO for evaluation; it is not yet a traditional hard-disk installer. Changes in the live environment are not persistent.

## Build

On a suitable **amd64 Debian** builder with root privileges, internet access, about 15 GB of free disk space:

```bash
sudo apt update
sudo apt install live-build dpkg-dev
bash vm/build-iso.sh
```

Or run the GitHub Action **Build VirtualBox Live ISO** manually and retrieve the workflow artifact if the build succeeds.

## Test in VirtualBox
- Linux / Debian (64-bit), 2 vCPUs, 2 GB RAM
- EFI disabled, VMSVGA graphics, 128 MB video memory, 3D acceleration disabled
- NAT networking (Bridged if you want to reach the dashboard from other LAN computers)
- Mount `KUFGEM-InfoScreenOS-VM-amd64.iso` in the virtual optical drive.
- Boot the ISO in Live mode. LightDM should automatically start the native InfoScreen display.

To open the dashboard on the host, easiest is **NAT port forwarding**: host TCP port 8080 to guest TCP port 8080. Then open `http://127.0.0.1:8080` on the host. VirtualBox bridged networking is an alternative.

Admin token resides at `/etc/kufgem-infoscreen/admin-token` inside the VM. Use a TTY console (Ctrl+Alt+F2, with VirtualBox host-key handling) to retrieve it with `sudo cat /etc/kufgem-infoscreen/admin-token`; return to the graphical session with Ctrl+Alt+F7 or the appropriate VT. This flow has **not been hardware/VM validated**.

## Limitations
- This ISO is for **VM testing**, not for flashing a Pi.
- The Pi's direct DRM/KMS display output is a separate hardware test.
- Live session data and any uploaded background images disappear at shutdown.
- The first ISO build is unverified; please report build errors before treating it as a release.
