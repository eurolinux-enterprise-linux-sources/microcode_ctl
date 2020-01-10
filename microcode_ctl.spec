%define upstream_version 2.1-18
%define intel_ucode_version 20190918
%define intel_ucode_file_id 28727

%define caveat_dir %{_datarootdir}/microcode_ctl/ucode_with_caveats
%define microcode_ctl_libexec %{_libexecdir}/microcode_ctl

%define update_ucode %{microcode_ctl_libexec}/update_ucode
%define check_caveats %{microcode_ctl_libexec}/check_caveats
%define reload_microcode %{microcode_ctl_libexec}/reload_microcode

%define dracutlibdir %{_prefix}/lib/dracut

%define i_m2u_man intel-microcode2ucode.8

# In microcode_ctl, documentation directory is unversioned historically.
# In RHEL 8 spec, %{_pkgdocdir} is used as installation destination; however,
# it is unversioned only since Fedora 20, per #986871,
# and not in Fedora 18/19-based RHEL 7.
%define _pkgdocdir %{_docdir}/%{name}

Summary:        Tool to transform and deploy CPU microcode update for x86.
Name:           microcode_ctl
Version:        2.1
Release:        53.2%{?dist}
Epoch:          2
Group:          System Environment/Base
License:        GPLv2+ and Redistributable, no modification permitted
URL:            https://pagure.io/microcode_ctl
Source0:        https://releases.pagure.org/microcode_ctl/%{name}-%{upstream_version}.tar.xz
Source1:        https://github.com/intel/Intel-Linux-Processor-Microcode-Data-Files/archive/microcode-%{intel_ucode_version}.tar.gz
# (Pre-MDS) revision 0x714 of 06-2d-07 microcode
Source2:        https://github.com/intel/Intel-Linux-Processor-Microcode-Data-Files/raw/microcode-20190514/intel-ucode/06-2d-07


# systemd unit
Source10:       microcode.service

# dracut-related stuff
Source20:       01-microcode.conf
Source21:       99-microcode-override.conf
Source22:       dracut_99microcode_ctl-fw_dir_override_module_init.sh

# libexec
Source30:       update_ucode
Source31:       check_caveats
Source32:       reload_microcode

# docs
Source40:       %{i_m2u_man}.in
Source41:       README.caveats

## Caveats
# BDW EP/EX
# https://bugzilla.redhat.com/show_bug.cgi?id=1622180
# https://bugzilla.redhat.com/show_bug.cgi?id=1623630
# https://bugzilla.redhat.com/show_bug.cgi?id=1646383
Source100:      06-4f-01_readme
Source101:      06-4f-01_config
Source102:      06-4f-01_disclaimer

# Unsafe early MC update inside VM:
# https://bugzilla.redhat.com/show_bug.cgi?id=1596627
Source110:      intel_readme
Source111:      intel_config
Source112:      intel_disclaimer

# SNB-EP (CPUID 0x206d7) post-MDS hangs
# https://bugzilla.redhat.com/show_bug.cgi?id=1758382
# https://github.com/intel/Intel-Linux-Processor-Microcode-Data-Files/issues/15
Source120:      06-2d-07_readme
Source121:      06-2d-07_config
Source122:      06-2d-07_disclaimer


# "Provides:" RPM tags generator
Source200:      gen_provides.sh

Patch1:         microcode_ctl-do-not-merge-ucode-with-caveats.patch
Patch2:         microcode_ctl-revert-intel-microcode2ucode-removal.patch
Patch3:         microcode_ctl-use-microcode-%{intel_ucode_version}-tgz.patch
Patch4:         microcode_ctl-do-not-install-intel-ucode.patch
Patch5:         microcode_ctl-intel-microcode2ucode-buf-handling.patch
Patch6:         microcode_ctl-ignore-first-directory-level-in-archive.patch

Buildroot:      %{_tmppath}/%{name}-%{version}-root
ExclusiveArch:  %{ix86} x86_64
BuildRequires:  systemd-units
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd
Requires(posttrans): kernel

%global _use_internal_dependency_generator 0
%define __find_provides "%{SOURCE200}"

%description
The microcode_ctl utility is a companion to the microcode driver written
by Tigran Aivazian <tigran@aivazian.fsnet.co.uk>.

The microcode update is volatile and needs to be uploaded on each system
boot i.e. it doesn't reflash your cpu permanently, reboot and it reverts
back to the old microcode.

%prep
%setup -q -n %{name}-%{upstream_version}
%patch1 -p1
%patch2 -p1

# Use the latest archive instead of microcode-20180703.tgz bundled
# with upstream microcode_ctl-2.1-18.
cp "%{SOURCE1}" .
%patch3 -p1

# We install ucode files manually into "intel" caveat directory
%patch4 -p1

%patch5 -p1

# The archive published on github has an additional top-level directory,
# strip it.
%patch6 -p1

%build
make CFLAGS="$RPM_OPT_FLAGS" %{?_smp_mflags}

# We do not populate any intel-ucode files into /lib/firmware directly due to
# early microcode load inside VM issue:
#   https://bugzilla.redhat.com/show_bug.cgi?id=1596627
#   https://bugzilla.redhat.com/show_bug.cgi?id=1607899
#find intel-ucode -type f | sed 's/^/%%ghost \/lib\/firmware\//' > ghost_list
touch ghost_list

tar xf "%{SOURCE1}" --wildcards --strip-components=1 \
	\*/intel-ucode-with-caveats \*/license \*/releasenote

# replacing SNB-EP (CPUID 0x206d7) microcode with pre-MDS version
mv intel-ucode/06-2d-07 intel-ucode-with-caveats/
cp "%{SOURCE2}" intel-ucode/

# man page
sed "%{SOURCE40}" \
	-e "s/@DATE@/2019-05-09/g" \
	-e "s/@VERSION@/%{version}-%{release}/g" \
	-e "s|@MICROCODE_URL@|https://downloadcenter.intel.com/download/%{intel_ucode_file_id}|g" > "%{i_m2u_man}"

%install
rm -rf %{buildroot}
make DESTDIR=%{buildroot} PREFIX=%{_prefix} INSDIR=/usr/sbin MICDIR=/usr/share/microcode_ctl install clean

install -m 755 -d \
	"%{buildroot}/%{_datarootdir}/microcode_ctl/intel-ucode" \
	"%{buildroot}/%{caveat_dir}/" \
	"%{buildroot}/etc/microcode_ctl/ucode_with_caveats/"

# systemd unit
install -m 755 -d "%{buildroot}/%{_unitdir}"
install -m 644 "%{SOURCE10}" -t "%{buildroot}/%{_unitdir}/"

# dracut
%define dracut_mod_dir "%{buildroot}/%{dracutlibdir}/modules.d/99microcode_ctl-fw_dir_override"
install -m 755 -d \
	"%{dracut_mod_dir}" \
	"%{buildroot}/%{dracutlibdir}/dracut.conf.d/"
install -m 644 "%{SOURCE20}" "%{SOURCE21}" \
	-t "%{buildroot}/%{dracutlibdir}/dracut.conf.d/"
install -m 755 "%{SOURCE22}" "%{dracut_mod_dir}/module-setup.sh"

# Internal helper scripts
install -m 755 -d "%{buildroot}/%{microcode_ctl_libexec}"
install "%{SOURCE30}" "%{SOURCE31}" "%{SOURCE32}" \
	-m 755 -t "%{buildroot}/%{microcode_ctl_libexec}"


## Documentation
install -m 755 -d "%{buildroot}/%{_pkgdocdir}/caveats"

# caveats readme
install "%{SOURCE41}" \
	-m 644 -t "%{buildroot}/%{_pkgdocdir}/"

# Provide Intel microcode license, as it requires so
install -m 644 license \
	"%{buildroot}/%{_pkgdocdir}/LICENSE.intel-ucode"

# Provide release notes for Intel microcode
install -m 644 releasenote \
	"%{buildroot}/%{_pkgdocdir}/RELEASE_NOTES.intel-ucode"

# caveats
install -m 644 "%{SOURCE100}" "%{SOURCE110}" "%{SOURCE120}" \
	-t "%{buildroot}/%{_pkgdocdir}/caveats/"

# Man page
install -m 755 -d %{buildroot}/%{_mandir}/man8/
install -m 644 "%{i_m2u_man}" -t %{buildroot}/%{_mandir}/man8/


## Caveat data

# BDW caveat
%define bdw_inst_dir %{buildroot}/%{caveat_dir}/intel-06-4f-01/
install -m 755 -d "%{bdw_inst_dir}/intel-ucode"
install -m 644 intel-ucode-with-caveats/06-4f-01 -t "%{bdw_inst_dir}/intel-ucode/"
install -m 644 "%{SOURCE100}" "%{bdw_inst_dir}/readme"
install -m 644 "%{SOURCE101}" "%{bdw_inst_dir}/config"
install -m 644 "%{SOURCE102}" "%{bdw_inst_dir}/disclaimer"

# Early update caveat
%define intel_inst_dir %{buildroot}/%{caveat_dir}/intel/
install -m 755 -d "%{intel_inst_dir}/intel-ucode"
install -m 644 intel-ucode/* -t "%{intel_inst_dir}/intel-ucode/"
install -m 644 "%{SOURCE110}" "%{intel_inst_dir}/readme"
install -m 644 "%{SOURCE111}" "%{intel_inst_dir}/config"
install -m 644 "%{SOURCE112}" "%{intel_inst_dir}/disclaimer"

# SNB caveat
%define snb_inst_dir %{buildroot}/%{caveat_dir}/intel-06-2d-07/
install -m 755 -d "%{snb_inst_dir}/intel-ucode"
install -m 644 intel-ucode-with-caveats/06-2d-07 -t "%{snb_inst_dir}/intel-ucode/"
install -m 644 "%{SOURCE120}" "%{snb_inst_dir}/readme"
install -m 644 "%{SOURCE121}" "%{snb_inst_dir}/config"
install -m 644 "%{SOURCE122}" "%{snb_inst_dir}/disclaimer"

# Cleanup
rm -f intel-ucode-with-caveats/06-4f-01
rm -f intel-ucode-with-caveats/06-2d-07
rmdir intel-ucode-with-caveats
rm -rf intel-ucode

%post
%systemd_post microcode.service
%{update_ucode}
%{reload_microcode}

# send the message to syslog, so it gets recorded on /var/log
if [ -e /usr/bin/logger ]; then
	%{check_caveats} -m -d | /usr/bin/logger -p syslog.notice -t DISCLAIMER
fi
# also paste it over dmesg (some customers drop dmesg messages while
# others keep them into /var/log for the later case, we'll have the
# disclaimer recorded twice into system logs.
%{check_caveats} -m -d > /dev/kmsg

exit 0

%posttrans
# We only want to regenerate the initramfs for a fully booted
# system; if this package happened to e.g. be pulled in as a build
# dependency, it is pointless at best to regenerate the initramfs,
# and also does not work with rpm-ostree:
# https://bugzilla.redhat.com/show_bug.cgi?id=1199582
#
# Also check that the running kernel is actually installed:
# https://bugzilla.redhat.com/show_bug.cgi?id=1591664
# We use the presence of symvers file as an indicator, the check similar
# to what weak-modules script does.
if [ -d /run/systemd/system -a -e "/boot/symvers-$(uname -r).gz" ]; then
	dracut -f
fi

%global rpm_state_dir %{_localstatedir}/lib/rpm-state


%preun
%systemd_preun microcode.service

# Storing ucode list before uninstall
ls /usr/share/microcode_ctl/intel-ucode |
	sort > "%{rpm_state_dir}/microcode_ctl_un_intel-ucode"
ls /usr/share/microcode_ctl/ucode_with_caveats |
	sort > "%{rpm_state_dir}/microcode_ctl_un_ucode_caveats"
%{update_ucode} --action list --skip-common |
	sort > "%{rpm_state_dir}/microcode_ctl_un_file_list"

%postun
%systemd_postun microcode.service

ls /usr/share/microcode_ctl/intel-ucode 2> /dev/null |
	sort > "%{rpm_state_dir}/microcode_ctl_un_intel-ucode_after"
comm -23 \
	"%{rpm_state_dir}/microcode_ctl_un_intel-ucode" \
	"%{rpm_state_dir}/microcode_ctl_un_intel-ucode_after" \
	> "%{rpm_state_dir}/microcode_ctl_un_intel-ucode_diff"

if [ -e "%{update_ucode}" ]; then
	ls /usr/share/microcode_ctl/ucode_with_caveats 2> /dev/null |
		sort > "%{rpm_state_dir}/microcode_ctl_un_ucode_caveats_after"

	comm -23 \
		"%{rpm_state_dir}/microcode_ctl_un_ucode_caveats" \
		"%{rpm_state_dir}/microcode_ctl_un_ucode_caveats_after" \
		> "%{rpm_state_dir}/microcode_ctl_un_ucode_caveats_diff"

	%{update_ucode} --action remove --cleanup \
		"%{rpm_state_dir}/microcode_ctl_un_intel-ucode_diff" \
		"%{rpm_state_dir}/microcode_ctl_un_ucode_caveats_diff" || exit 0

	rm -f "%{rpm_state_dir}/microcode_ctl_un_ucode_caveats_after"
	rm -f "%{rpm_state_dir}/microcode_ctl_un_ucode_caveats_diff"
else
	while read -r f; do
		[ -L "/lib/firmware/intel-ucode/$f" ] || continue
		rm -f "/lib/firmware/intel-ucode/$f"
	done < "%{rpm_state_dir}/microcode_ctl_un_intel-ucode_diff"

	rmdir "/lib/firmware/intel-ucode" 2>/dev/null || :

	# We presume that if we don't have update_ucode script, we can remove
	# all the caveats-related files.
	while read -r f; do
		if [ -L "$f" ] || [ "${f%%readme-*}" != "$f" ]; then
			rm -f "$f"
			rmdir -p $(dirname "$f") 2>/dev/null || :
		fi
	done < "%{rpm_state_dir}/microcode_ctl_un_file_list"
fi

rm -f "%{rpm_state_dir}/microcode_ctl_un_intel-ucode"
rm -f "%{rpm_state_dir}/microcode_ctl_un_intel-ucode_after"
rm -f "%{rpm_state_dir}/microcode_ctl_un_intel-ucode_diff"

rm -f "%{rpm_state_dir}/microcode_ctl_un_ucode_caveats"

rm -f "%{rpm_state_dir}/microcode_ctl_un_file_list"


exit 0

%triggerin -- kernel
%{update_ucode}

%triggerpostun -- kernel
%{update_ucode}


%clean
rm -rf %{buildroot}

%files -f ghost_list
%ghost %attr(0755, root, root) /lib/firmware/intel-ucode/
/usr/sbin/intel-microcode2ucode
%{microcode_ctl_libexec}
/usr/share/microcode_ctl
%{dracutlibdir}/modules.d/*
%config(noreplace) %{dracutlibdir}/dracut.conf.d/*
%{_unitdir}/microcode.service
%doc %{_pkgdocdir}
%{_mandir}/man8/*


%changelog
* Sun Oct 06 2019 Eugene Syromiatnikov <esyr@redhat.com> - 2:2.1-53.2
- Do not update 06-2d-07 (SNB-E/EN/EP) to revision 0x718, use 0x714
  by default.

* Thu Sep 19 2019 Eugene Syromiatnikov <esyr@redhat.com> - 2:2.1-53.1
- Intel CPU microcode update to 20190918.
- Add new disclaimer, generated based on relevant caveats.
- Resolves: #1758572.

* Wed Jun 19 2019 Eugene Syromiatnikov <esyr@redhat.com> - 2:2.1-53
- Intel CPU microcode update to 20190618.
- Resolves: #1717241.

* Sun Jun 02 2019 Eugene Syromiatnikov <esyr@redhat.com> - 2:2.1-52
- Remove disclaimer, as it is not as important now to justify kmsg/log
  pollution; its contents are partially adopted in README.caveats.

* Mon May 20 2019 Eugene Syromiatnikov <esyr@redhat.com> - 2:2.1-51
- Intel CPU microcode update to 20190514a.
- Resolves: #1711941.

* Thu May 09 2019 Eugene Syromiatnikov <esyr@redhat.com> - 2:2.1-50
- Intel CPU microcode update to 20190507_Public_DEMO.
- Resolves: #1697904.

* Mon Apr 15 2019 Eugene Syromiatnikov <esyr@redhat.com> - 2:2.1-49
- Intel CPU microcode update to 20190312.
- Add "Provides:" tags generation.
- Resolves: #1697904.

* Thu Sep 20 2018 Eugene Syromiatnikov <esyr@redhat.com> - 2:2.1-48
- Fix %postun script (#1628629)

* Wed Sep 05 2018 Eugene Syromiatnikov <esyr@redhat.com> - 2:2.1-47
- Add 7.3.z kernel version to kernel_early configuration.

* Thu Aug 30 2018 Eugene Syromiatnikov <esyr@redhat.com> - 2:2.1-46
- Fix dracut module checks in Host-Only mode.

* Thu Aug 30 2018 Eugene Syromiatnikov <esyr@redhat.com> - 2:2.1-45
- Disable 06-4f-01 microcode in config (#1623630).

* Tue Aug 28 2018 Eugene Syromiatnikov <esyr@redhat.com> - 2:2.1-44
- Intel CPU microcode update to 20180807a.
- Add README.caveats documentation file.
- Add intel-microcode2ucode manual page.
- Add check for early microcode load, use it in microcode_ctl dracut module.
- Resolves: #1596627.

* Mon Aug 20 2018 Eugene Syromiatnikov <esyr@redhat.com> - 2:2.1-43
- Check that the currently running kernel is installed before
  running dracut -f.

* Thu Aug 16 2018 Eugene Syromiatnikov <esyr@redhat.com> - 2:2.1-42
- Drop "hypervisor" /proc/cpuinfo flag check.

* Thu Aug 09 2018 Eugene Syromiatnikov <esyr@redhat.com> - 2:2.1-41
- Intel CPU microcode update to 20180807.
- Resolves: #1614422

* Mon Aug 06 2018 Eugene Syromiatnikov <esyr@redhat.com> - 2:2.1-40
- Add an ability to disable "hypervisor" /proc/cpuinfo flag check.

* Fri Jul 27 2018 Eugene Syromiatnikov <esyr@redhat.com> - 2:2.1-39
- Provide %attr for the ghosted /lib/firmware/intel-ucode.

* Thu Jul 26 2018 Eugene Syromiatnikov <esyr@redhat.com> - 2:2.1-38
- Remove model name blacklists from caveats configuration files.
- Resolves: #1596627

* Wed Jul 25 2018 Eugene Syromiatnikov <esyr@redhat.com> - 2:2.1-37
- Add model name blacklist infrastructure.
- Store Intel ucode files in /usr/share/microcode_ctl; do not populate them
  in a virtualised environment.
- Resolves: #1596627

* Fri Jul 20 2018 Eugene Syromiatnikov <esyr@redhat.com> - 2:2.1-35
- Add intel-microcode2ucode back
- Resolves: #1574582

* Fri Jul 20 2018 Eugene Syromiatnikov <esyr@redhat.com> - 2:2.1-34
- Update to upstream 2.1-18. Intel CPU microcode update to 20180703.
- Add infrastructure for handling kernel-version-dependant microcode.
- Resolves: #1574582

* Wed Jun 13 2018 Petr Oros <poros@redhat.com> - 2.1-33
- CVE-2018-3639 hw: cpu: speculative store bypass
- Resolves: #1495071

* Mon Jun 11 2018 Petr Oros <poros@redhat.com> - 2.1-32
- Fix: Operation not permitted when installing microcode_ctl
- Resolves: #1584247

* Tue May 15 2018 Petr Oros <poros@redhat.com> - 2.1-31
- Update disclaimer text
- Resolves: #1574574

* Mon May 7 2018 Petr Oros <poros@redhat.com> - 2.1-30
- Intel CPU microcode update to 20180425.
- Resolves: #1574574

* Fri Jan 12 2018 Petr Oros <poros@redhat.com> - 2.1-29
- Revert Microcode from Intel for Side Channel attack
- Resolves: #1533939

* Fri Jan 12 2018 Petr Oros <poros@redhat.com> - 2.1-29
- Don't run dracut if not on a live system
- Resolves: #1530400

* Tue Jan 9 2018 Petr Oros <poros@redhat.com> - 2.1-28
- Remove old binary tool
- Resolves: #1527360

* Tue Jan 9 2018 Petr Oros <poros@redhat.com> - 2.1-27
- Update to upstream 2.1-15. Intel CPU microcode update to 20180108.
- Resolves: #1527360

* Fri Dec 15 2017 Petr Oros <poros@redhat.com> - 2.1-26
- Update Intel CPU microde for 06-3f-02, 06-4f-01, and 06-55-04
- Resolves: #1527360

* Wed Nov 22 2017 Petr Oros <poros@redhat.com> - 2.1-25
- Update to upstream 2.1-14. Intel CPU microcode update to 20171117.
- Resolves: #1457522

* Tue Oct 17 2017 Petr Oros <poros@redhat.com> - 2.1-24
- Fix upstream URL
- Resolves: #1502360

* Fri Jul 14 2017 Petr Oros <poros@redhat.com> - 2.1-23
- Update to upstream 2.1-13. Intel CPU microcode update to 20170707.
- Resolves: #1457522

* Wed May 24 2017 Petr Oros <poros@redhat.com> - 2.1-22
- Update to upstream 2.1-12. Intel CPU microcode update to 20170511.
- Resolves: #1384218

* Tue Mar 7 2017 Petr Oros <poros@redhat.com> - 2.1-21
- Rpm scriptlets should only rebuild the current kernel's initrd.
- Resolves: #1420180

* Wed Jan 18 2017 Petr Oros <poros@redhat.com> - 2.1-20
- Fix issue with hot microcode cpu reload.
- Resolves: #1411232

* Mon Jan 9 2017 Petr Oros <poros@redhat.com> - 2.1-19
- Fix broken quoting in ExecStart line.
- Resolves: #1411232

* Fri Dec 16 2016 Petr Oros <poros@redhat.com> - 2.1-18
- Fix issue with hot microcode cpu reload.
- Resolves: #1398698

* Wed Nov 30 2016 Petr Oros <poros@redhat.com> - 2.1-17
- Move dracut call into posttrans phase.
- Resolves: #1398698

* Thu Jul 21 2016 Petr Oros <poros@redhat.com> - 2.1-16
- Update to upstream 2.1-10. Intel CPU microcode update to 20160714.
- Resolves: #1358047

* Wed Jun 29 2016 Petr Oros <poros@redhat.com> - 2.1-15
- Load CPU microcode update only on supproted systems.
- Resolves: #1307179

* Fri Jun 24 2016 Petr Oros <poros@redhat.com> - 2.1-14
- Update to upstream 2.1-9. Intel CPU microcode update to 20160607.
- Resolves: #1253106

* Thu May 19 2016 Petr Oros <poros@redhat.com> - 2.1-13
- Run dracut -f for all kernels.
- Resolves: #1292158

* Fri Jul 3 2015 Petr Oros <poros@redhat.com> - 2.1-12
- Update to upstream 2.1-7. Intel CPU microcode update to 20150121.
- Resolves: #1174983

* Fri Oct 10 2014 Petr Oros <poros@redhat.com> - 2.1-11
- Run dracut -f after install microcode for update initramfs.
- Resolves: #1151192

* Tue Sep 30 2014 Petr Oros <poros@redhat.com> - 2.1-10
- Update to upstream 2.1-6. Intel CPU microcode update to 20140913.
- Resolves: #1142302

* Tue Jul 15 2014 Petr Oros <poros@redhat.com> - 2.1-9
- Update to upstream 2.1-5. Intel CPU microcode update to 20140624.
- Resolves: #1113396

* Tue Jun 3 2014 Petr Oros <poros@redhat.com> - 2.1-8
- Fix bogus time in changelog
- Resolves: #1085117

* Tue Jun 3 2014 Petr Oros <poros@redhat.com> - 2.1-8
- Update to upstream 2.1-4. Intel CPU microcode update to 20140430.
- Resolves: #1085117

* Wed Mar 12 2014 Anton Arapov <anton@redhat.com> - 2.1-7.1
- Fix the microcode's behaviour in virtual environment.

* Fri Feb 28 2014 Anton Arapov <anton@redhat.com> - 2.1-7
- Fix the microcode's dracut configuration file location. 

* Tue Feb 18 2014 Anton Arapov <anton@redhat.com> - 2.1-6
- Enable early microcode capabilities. Systemd and Dracut support. (Jeff Bastian)

* Fri Jan 24 2014 Anton Arapov <anton@redhat.com> - 2.1-5
- Update to upstream 2.1-3. Intel CPU microcode update to 20140122.

* Fri Dec 27 2013 Daniel Mach <dmach@redhat.com> - 2:2.1-4
- Mass rebuild 2013-12-27

* Mon Sep 09 2013 Anton Arapov <anton@redhat.com> 2.1-3
- Imported to RHEL tree

* Mon Sep 09 2013 Anton Arapov <anton@redhat.com> 2.1-2
- Update to upstream 2.1-2.

* Wed Aug 14 2013 Anton Arapov <anton@redhat.com> 2.1-1
- Update to upstream 2.1-1.

* Sat Jul 27 2013 Anton Arapov <anton@redhat.com> 2.1-0
- Update to upstream 2.1. AMD microcode has been removed, find it in linux-firmware.

* Wed Apr 03 2013 Anton Arapov <anton@redhat.com> 2.0-3.1
- Update to upstream 2.0-3

* Thu Feb 14 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2:2.0-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Wed Oct 17 2012 Anton Arapov <anton@redhat.com> 2.0-2
- Update to upstream 2.0-2

* Tue Oct 02 2012 Anton Arapov <anton@redhat.com> 2.0-1
- Update to upstream 2.0-1

* Mon Aug 06 2012 Anton Arapov <anton@redhat.com> 2.0
- Update to upstream 2.0

* Wed Jul 25 2012 Anton Arapov <anton@redhat.com> 1.18-1
- Update to upstream 1.18

* Fri Jul 20 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1:1.17-26
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Thu Jun 07 2012 Anton Arapov <anton@redhat.com> 1.17-25
- Update to microcode-20120606.dat

* Tue Feb 07 2012 Anton Arapov <anton@redhat.com> 1.17-24
- Update to amd-ucode-2012-01-17.tar

* Fri Jan 13 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1:1.17-22
- Rebuilt for https://fedoraproject.org/wiki/Fedora_17_Mass_Rebuild

* Thu Dec 22 2011 Anton Arapov <anton@redhat.com> 1.17-21
- Fix a segfault that may be triggered by very long parameter [#768803]

* Tue Dec 13 2011 Anton Arapov <anton@redhat.com> 1.17-20
- Update to microcode-20111110.dat

* Tue Sep 27 2011 Anton Arapov <anton@redhat.com> 1.17-19
- Update to microcode-20110915.dat

* Thu Aug 04 2011 Anton Arapov <anton@redhat.com> 1.17-18
- Ship splitted microcode for Intel CPUs [#690930]
- Include tool for splitting microcode for Intl CPUs (Kay Sievers )

* Thu Jun 30 2011 Anton Arapov <anton@redhat.com> 1.17-17
- Fix udev rules (Dave Jones ) [#690930]

* Thu May 12 2011 Anton Arapov <anton@redhat.com> 1.17-14
- Update to microcode-20110428.dat

* Thu Mar 24 2011 Anton Arapov <anton@redhat.com> 1.17-13
- fix memory leak.

* Mon Mar 07 2011 Anton Arapov <anton@redhat.com> 1.17-12
- Update to amd-ucode-2011-01-11.tar

* Tue Feb 08 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1:1.17-11
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Wed Jan 19 2011 Anton Arapov <anton@redhat.com> 1.17-10
- manpage fix (John Bradshaw ) [#670879]

* Wed Jan 05 2011 Anton Arapov <anton@redhat.com> 1.17-9
- Update to microcode-20101123.dat

* Mon Nov 01 2010 Anton Arapov <anton@redhat.com> 1.17-8
- Update to microcode-20100914.dat

* Wed Sep 29 2010 jkeating - 1:1.17-7
- Rebuilt for gcc bug 634757

* Wed Sep 15 2010 Anton Arapov <anton@redhat.com> 1.17-6
- Update to microcode-20100826.dat

* Tue Sep 07 2010 Toshio Kuratomi <toshio@fedoraproject.org> 1.17-5
- Fix license tag: bz#450491

* Fri Aug 27 2010 Dave Jones <davej@redhat.com> 1.17-4
- Update to microcode-20100826.dat

* Tue Mar 23 2010 Anton Arapov <anton@redhat.com> 1.17-3
- Fix the udev rules (Harald Hoyer )

* Mon Mar 22 2010 Anton Arapov <anton@redhat.com> 1.17-2
- Make microcode_ctl event driven (Bill Nottingham ) [#479898]

* Thu Feb 11 2010 Dave Jones <davej@redhat.com> 1.17-1.58
- Update to microcode-20100209.dat

* Fri Dec 04 2009 Kyle McMartin <kyle@redhat.com> 1.17-1.57
- Fix duplicate message pointed out by Edward Sheldrake.

* Wed Dec 02 2009 Kyle McMartin <kyle@redhat.com> 1.17-1.56
- Add AMD x86/x86-64 microcode. (Dated: 2009-10-09)
  Doesn't need microcode_ctl modifications as it's loaded by
  request_firmware() like any other sensible driver.
- Eventually, this AMD firmware can probably live inside
  kernel-firmware once it is split out.

* Wed Sep 30 2009 Dave Jones <davej@redhat.com>
- Update to microcode-20090927.dat

* Fri Sep 11 2009 Dave Jones <davej@redhat.com>
- Remove some unnecessary code from the init script.

* Sat Jul 25 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1:1.17-1.52.1
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Thu Jun 25 2009 Dave Jones <davej@redhat.com>
- Shorten sleep time during init.
  This really needs to be replaced with proper udev hooks, but this is
  a quick interim fix.

* Wed Jun 03 2009 Kyle McMartin <kyle@redhat.com> 1:1.17-1.50
- Change ExclusiveArch to i586 instead of i386. Resolves rhbz#497711.

* Wed May 13 2009 Dave Jones <davej@redhat.com>
- update to microcode 20090330

* Wed Feb 25 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1:1.17-1.46.1
- Rebuilt for https://fedoraproject.org/wiki/Fedora_11_Mass_Rebuild

* Fri Sep 12 2008 Dave Jones <davej@redhat.com>
- update to microcode 20080910

* Tue Apr 01 2008 Jarod Wilson <jwilson@redhat.com>
- Update to microcode 20080401

* Sat Mar 29 2008 Dave Jones <davej@redhat.com>
- Update to microcode 20080220
- Fix rpmlint warnings in specfile.

* Mon Mar 17 2008 Dave Jones <davej@redhat.com>
- specfile cleanups.

* Fri Feb 22 2008 Jarod Wilson <jwilson@redhat.com>
- Use /lib/firmware instead of /etc/firmware

* Wed Feb 13 2008 Jarod Wilson <jwilson@redhat.com>
- Fix permissions on microcode.dat

* Thu Feb 07 2008 Jarod Wilson <jwilson@redhat.com>
- Spec cleanup and macro standardization.
- Update license
- Update microcode data file to 20080131 revision.

* Mon Jul  2 2007 Dave Jones <davej@redhat.com>
- Update to upstream 1.17

* Thu Oct 12 2006 Jon Masters <jcm@redhat.com>
- BZ209455 fixes.

* Mon Jul 17 2006 Jesse Keating <jkeating@redhat.com>
- rebuild

* Fri Jun 16 2006 Bill Nottingham <notting@redhat.com>
- remove kudzu requirement
- add prereq for coreutils, awk, grep

* Thu Feb 09 2006 Dave Jones <davej@redhat.com>
- rebuild.

* Fri Jan 27 2006 Dave Jones <davej@redhat.com>
- Update to upstream 1.13

* Fri Dec 16 2005 Jesse Keating <jkeating@redhat.com>
- rebuilt for new gcj

* Fri Dec 09 2005 Jesse Keating <jkeating@redhat.com>
- rebuilt

* Mon Nov 14 2005 Dave Jones <davej@redhat.com>
- initscript tweaks.

* Tue Sep 13 2005 Dave Jones <davej@redhat.com>
- Update to upstream 1.12

* Wed Aug 17 2005 Dave Jones <davej@redhat.com>
- Check for device node *after* loading the module. (#157672)

* Tue Mar  1 2005 Dave Jones <davej@redhat.com>
- Rebuild for gcc4

* Thu Feb 17 2005 Dave Jones <davej@redhat.com>
- s/Serial/Epoch/

* Tue Jan 25 2005 Dave Jones <davej@redhat.com>
- Drop the node creation/deletion change from previous release.
  It'll cause grief with selinux, and was a hack to get around
  a udev shortcoming that should be fixed properly.

* Fri Jan 21 2005 Dave Jones <davej@redhat.com>
- Create/remove the /dev/cpu/microcode dev node as needed.
- Use correct path again for the microcode.dat.
- Remove some no longer needed tests in the init script.

* Fri Jan 14 2005 Dave Jones <davej@redhat.com>
- Only enable microcode_ctl service if the CPU is capable.
- Prevent microcode_ctl getting restarted multiple times on initlevel change (#141581)
- Make restart/reload work properly
- Do nothing if not started by root.

* Wed Jan 12 2005 Dave Jones <davej@redhat.com>
- Adjust dev node location. (#144963)

* Tue Jan 11 2005 Dave Jones <davej@redhat.com>
- Load/Remove microcode module in initscript.

* Mon Jan 10 2005 Dave Jones <davej@redhat.com>
- Update to upstream 1.11 release.

* Sat Dec 18 2004 Dave Jones <davej@redhat.com>
- Initial packaging, based upon kernel-utils.

