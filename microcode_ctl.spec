%define intel_ucode_version 20191112

Summary:        Tool to update x86/x86-64 CPU microcode.
Name:           microcode_ctl
Version:        1.17
Release:        33.19%{?dist}
Epoch:          2
Group:          System Environment/Base
License:        GPLv2+
URL:            https://pagure.io/microcode_ctl/
Source0:        https://releases.pagure.org/microcode_ctl/microcode_ctl-%{version}.tar.gz
Source1:        microcode_ctl.rules
# Microcode is now distributed directly by Intel, at
# https://github.com/intel/Intel-Linux-Processor-Microcode-Data-Files/
# (as referenced in https://downloadmirror.intel.com/28727/eng/Intel-Linux_Processor_Microcode_readme.txt )
Source2:        microcode-%{intel_ucode_version}.pre.tar.gz
# http://www.amd64.org/support/microcode.html
Source3:        amd-ucode-2018-05-24.tar
Source5:        intel_ucode2microcode
Source6:        check_caveats
Source7:        reload_microcode

# BDW EP/EX caveat
# https://bugzilla.redhat.com/show_bug.cgi?id=1622180
# https://bugzilla.redhat.com/show_bug.cgi?id=1623630
# https://bugzilla.redhat.com/show_bug.cgi?id=1646383
Source8:        06-4f-01_config
Source9:        06-4f-01_readme

Source10:       README.caveats

# SNB-EP (CPUID 0x206d7) post-MDS hangs
# https://bugzilla.redhat.com/show_bug.cgi?id=1758382
# https://github.com/intel/Intel-Linux-Processor-Microcode-Data-Files/issues/15
Source11:       https://github.com/intel/Intel-Linux-Processor-Microcode-Data-Files/raw/microcode-20190514/intel-ucode/06-2d-07
Source12:       06-2d-07_config
Source13:       06-2d-07_readme

Buildroot:      %{_tmppath}/%{name}-%{version}-root
Requires(pre):  /sbin/chkconfig /sbin/service
Requires(pre):  grep gawk coreutils
ExclusiveArch:  %{ix86} x86_64

Patch1: microcode_ctl.patch
Patch2: microcode_ctl-manpage-0.patch
Patch3: microcode_ctl-1.17-getopt.patch
Patch4: microcode_ctl-1.17-hosts-only.patch
Patch5: microcode_ctl-Broadwell-fix.patch

%description
microcode_ctl - updates the microcode on Intel x86/x86-64 CPU's

%prep
%setup -q
%patch1 -p1
%patch2 -p1
%patch3 -p1
%patch4 -p1
%patch5 -p1

# The archive published on github has an additional top-level
# directory, strip it.
tar xf %{SOURCE2} --wildcards --strip-components=1 \
	\*/intel-ucode \*/intel-ucode-with-caveats \*/license \*/releasenote

tar xf %{SOURCE3}

%build
make CFLAGS="$RPM_OPT_FLAGS" %{?_smp_mflags}

mv intel-ucode/06-2d-07 intel-ucode-with-caveats
cp "%{SOURCE11}" intel-ucode/

bash -efu %{SOURCE5} "intel-ucode" microcode.dat
bash -efu %{SOURCE5} "intel-ucode-with-caveats/06-4f-01" microcode-06-4f-01.dat
bash -efu %{SOURCE5} "intel-ucode-with-caveats/06-2d-07" microcode-06-2d-07.dat

%install
rm -rf %{buildroot}

mkdir -p %{buildroot}/lib/udev/rules.d
mkdir -p %{buildroot}/usr/share/man/man{1,8}
mkdir -p %{buildroot}%{_sysconfdir}/sysconfig
mkdir -p %{buildroot}/lib/firmware/amd-ucode/
mkdir -p %{buildroot}/usr/share/doc/microcode_ctl/
mkdir -p %{buildroot}/usr/libexec/microcode_ctl/
mkdir -p %{buildroot}/usr/share/microcode_ctl/ucode_with_caveats/intel-06-4f-01
mkdir -p %{buildroot}/usr/share/microcode_ctl/ucode_with_caveats/intel-06-2d-07

make DESTDIR=%{buildroot} PREFIX=%{_prefix} \
     INSDIR=/sbin MANDIR=%{_mandir}/man8 RCDIR=%{_sysconfdir} install clean

rm -rf %{buildroot}/etc/*

install -m 644 %{SOURCE1} %{buildroot}/lib/udev/rules.d/89-microcode.rules
install -m 644 microcode.dat %{buildroot}/lib/firmware/microcode.dat
install -m 644 microcode-06-4f-01.dat %{buildroot}/lib/firmware/microcode-06-4f-01.dat
install -m 644 microcode-06-2d-07.dat %{buildroot}/lib/firmware/microcode-06-2d-07.dat
install -m 644 %{SOURCE10} README.caveats

# Provide Intel microcode license, as it requires
install -m 644 license LICENSE.intel-ucode
install -m 644 releasenote RELEASE_NOTES.intel-ucode

install -m 755 %{SOURCE6} %{buildroot}/usr/libexec/microcode_ctl/check_caveats
install -m 755 %{SOURCE7} %{buildroot}/usr/libexec/microcode_ctl/reload_microcode

install -m 644 %{SOURCE8} %{buildroot}/usr/share/microcode_ctl/ucode_with_caveats/intel-06-4f-01/config
install -m 644 %{SOURCE9} %{buildroot}/usr/share/microcode_ctl/ucode_with_caveats/intel-06-4f-01/readme

install -m 644 %{SOURCE12} %{buildroot}/usr/share/microcode_ctl/ucode_with_caveats/intel-06-2d-07/config
install -m 644 %{SOURCE13} %{buildroot}/usr/share/microcode_ctl/ucode_with_caveats/intel-06-2d-07/readme

install -m 644 amd-ucode-2018-05-24/LICENSE.amd-ucode LICENSE.amd-ucode
install -m 644 amd-ucode-2018-05-24/microcode_amd.bin %{buildroot}/lib/firmware/amd-ucode/microcode_amd.bin
install -m 644 amd-ucode-2018-05-24/microcode_amd.bin.asc %{buildroot}/lib/firmware/amd-ucode/microcode_amd.bin.asc
install -m 644 amd-ucode-2018-05-24/microcode_amd_fam15h.bin %{buildroot}/lib/firmware/amd-ucode/microcode_amd_fam15h.bin
install -m 644 amd-ucode-2018-05-24/microcode_amd_fam15h.bin.asc %{buildroot}/lib/firmware/amd-ucode/microcode_amd_fam15h.bin.asc
install -m 644 amd-ucode-2018-05-24/microcode_amd_fam16h.bin %{buildroot}/lib/firmware/amd-ucode/microcode_amd_fam16h.bin
install -m 644 amd-ucode-2018-05-24/microcode_amd_fam16h.bin.asc %{buildroot}/lib/firmware/amd-ucode/microcode_amd_fam16h.bin.asc
install -m 644 amd-ucode-2018-05-24/microcode_amd_fam17h.bin %{buildroot}/lib/firmware/amd-ucode/microcode_amd_fam17h.bin
install -m 644 amd-ucode-2018-05-24/microcode_amd_fam17h.bin.asc %{buildroot}/lib/firmware/amd-ucode/microcode_amd_fam17h.bin.asc

chmod -R a-s %{buildroot}

mkdir -p "%{buildroot}/etc/microcode_ctl/ucode_with_caveats"

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root)
/etc/microcode_ctl
/lib/firmware/*
/lib/udev/rules.d/*
/sbin/microcode_ctl
/usr/libexec/microcode_ctl
/usr/share/microcode_ctl
%doc LICENSE.amd-ucode LICENSE.intel-ucode RELEASE_NOTES.intel-ucode README.caveats
%attr(0644,root,root) %{_mandir}/*/*

%triggerun -- microcode_ctl < 1:1.17-4
/sbin/chkconfig --del microcode_ctl
exit 0

%changelog
* Thu Nov 07 2019 Eugene Syromiatnikov <esyr@redhat.com> - 2:1.17-33.19
- Fix the incorrect "Source2:" tag.

* Thu Nov 07 2019 Eugene Syromiatnikov <esyr@redhat.com> - 2:1.17-33.18
- Intel CPU microcode update to 20191112, addresses CVE-2017-5715,
  CVE-2019-0117, CVE-2019-11135, CVE-2019-11139 (#1764049, #1764062, #1764953,
  #1764961, #1764988, #1765393, #1765405, #1766440, #1766862):
  - Addition of 06-a6-00/0x80 (CML-U 6+2 A0) microcode at revision 0xc6;
  - Addition of 06-66-03/0x80 (CNL-U D0) microcode at revision 0x2a;
  - Addition of 06-55-03/0x97 (SKL-SP B1) microcode at revision 0x1000150;
  - Addition of 06-7e-05/0x80 (ICL-U/Y D1) microcode at revision 0x46;
  - Update of 06-4e-03/0xc0 (SKL-U/Y D0) microcode from revision 0xcc to 0xd4;
  - Update of 06-5e-03/0x36 (SKL-H/S/Xeon E3 R0/N0) microcode from revision 0xcc
    to 0xd4
  - Update of 06-8e-09/0x10 (AML-Y 2+2 H0) microcode from revision 0xb4 to 0xc6;
  - Update of 06-8e-09/0xc0 (KBL-U/Y H0) microcode from revision 0xb4 to 0xc6;
  - Update of 06-8e-0a/0xc0 (CFL-U 4+3e D0) microcode from revision 0xb4
    to 0xc6;
  - Update of 06-8e-0b/0xd0 (WHL-U W0) microcode from revision 0xb8 to 0xc6;
  - Update of 06-8e-0c/0x94 (AML-Y V0) microcode from revision 0xb8 to 0xc6;
  - Update of 06-8e-0c/0x94 (CML-U 4+2 V0) microcode from revision 0xb8 to 0xc6;
  - Update of 06-8e-0c/0x94 (WHL-U V0) microcode from revision 0xb8 to 0xc6;
  - Update of 06-9e-09/0x2a (KBL-G/X H0) microcode from revision 0xb4 to 0xc6;
  - Update of 06-9e-09/0x2a (KBL-H/S/Xeon E3 B0) microcode from revision 0xb4
    to 0xc6;
  - Update of 06-9e-0a/0x22 (CFL-H/S/Xeon E U0) microcode from revision 0xb4
    to 0xc6;
  - Update of 06-9e-0b/0x02 (CFL-S B0) microcode from revision 0xb4 to 0xc6;
  - Update of 06-9e-0d/0x22 (CFL-H R0) microcode from revision 0xb8 to 0xc6.

* Sun Oct 06 2019 Eugene Syromiatnikov <esyr@redhat.com> - 2:1.17-33.17
- Do not update 06-2d-07 (SNB-E/EN/EP) to revision 0x718, use 0x714
  by default (#1758382).

* Sun Oct 06 2019 Eugene Syromiatnikov <esyr@redhat.com> - 2:1.17-33.16
- Revert more strict model check code, as it requires request_firmware-based
  microcode loading mechanism and breaks enabling of microcode with caveats.

* Thu Sep 19 2019 Eugene Syromiatnikov <esyr@redhat.com> - 2:1.17-33.15
- Intel CPU microcode update to 20190918 (#1753540).

* Wed Jun 19 2019 Eugene Syromiatnikov <esyr@redhat.com> - 2:1.17-33.14
- Intel CPU microcode update to 20190618 (#1717238).

* Sun Jun 02 2019 Eugene Syromiatnikov <esyr@redhat.com> - 2:1.17-33.13
- Remove disclaimer, as it is not as important now to justify kmsg/log
  pollution; its contents are partially adopted in README.caveats.

* Mon May 20 2019 Eugene Syromiatnikov <esyr@redhat.com> - 2:1.17-33.12
- Intel CPU microcode update to 20190514a (#1711938).

* Thu May 09 2019 Eugene Syromiatnikov <esyr@redhat.com> - 2:1.17-33.11
- Intel CPU microcode update to 20190507_Public_DEMO (#1697960).

* Mon May 06 2019 Eugene Syromiatnikov <esyr@redhat.com> - 2:1.17-33.10
- Intel CPU microcode update to 20190312 (#1697960).

* Fri Sep 07 2018 Eugene Syromiatnikov <esyr@redhat.com> - 2:1.17-33.9
- Fix disclaimer path in %post script.

* Thu Sep 06 2018 Eugene Syromiatnikov <esyr@redhat.com> - 2:1.17-33.8
- Fix installation path for the disclaimer file.
- Add README.caveats documentation file.

* Thu Aug 30 2018 Eugene Syromiatnikov <esyr@redhat.com> - 2:1.17-33.7
- Use check_caveats from the RHEL 7 package in order to support overrides.

* Thu Aug 30 2018 Eugene Syromiatnikov <esyr@redhat.com> - 2:1.17-33.6
- Disable 06-4f-01 microcode in config (#1622180).

* Fri Aug 24 2018 Eugene Syromiatnikov <esyr@redhat.com> - 2:1.17-33.5
- Intel CPU microcode update to 20180807a (#1614427).
- Add check for minimal microcode version to reload_microcode.

* Thu Aug 09 2018 Eugene Syromiatnikov <esyr@redhat.com> - 2:1.17-33.4
- Intel CPU microcode update to 20180807.
- Resolves: #1614427.

* Thu Jul 19 2018 Eugene Syromiatnikov <esyr@redhat.com> - 2:1.17-33.3
- Intel CPU microcode update to 20180703
- Add infrastructure for handling kernel-version-dependant microcode
- Resolves: #1574593

* Wed Jun 13 2018 Petr Oros <poros@redhat.com> - 1:1.17-33.1
- Intel CPU microcode update to 20180613.
- Resolves: #1573451

* Mon May 28 2018 Petr Oros <poros@redhat.com> - 1:1.17-33
- Update AMD microcode to 2018-05-24
- Resolves: #1584192

* Fri May 18 2018 Petr Oros <poros@redhat.com> - 1:1.17-32
- Update AMD microcode
- Resolves: #1574591

* Tue May 15 2018 Petr Oros <poros@redhat.com> - 1:1.17-31
- Update disclaimer text
- Resolves: #1574588

* Mon May 7 2018 Petr Oros <poros@redhat.com> - 1:1.17-30
- Intel CPU microcode update to 20180425.
- Resolves: #1574588

* Fri Jan 12 2018 Petr Oros <poros@redhat.com> - 1:1.17-29
- Revert Microcode from Intel and AMD for Side Channel attack
- Resolves: #1533941

* Wed Jan 10 2018 Petr Oros <poros@redhat.com> - 1:1.17-28
- Update microcode data file to 20180108 revision.
- Resolves: #1527354

* Fri Dec 15 2017 Petr Oros <poros@redhat.com> - 1:1.17-27
- Update Intel CPU microde for 06-3f-02, 06-4f-01, and 06-55-04
- Add amd microcode_amd_fam17h.bin data file
- Resolves: #1527354

* Mon Jul 17 2017 Petr Oros <poros@redhat.com> - 1:1.17-26
- Update microcode data file to 20170707 revision.
- Resolves: #1465143

* Mon Feb 20 2017 Petr Oros <poros@redhat.com> - 1:1.17-25
- Revert microcode_amd_fam15h.bin to version from amd-ucode-2012-09-10
- Resolves: #1322525

* Tue Feb 7 2017 Petr Oros <poros@redhat.com> - 1:1.17-24
- Update microcode data file to 20161104 revision.
- Add workaround for E5-26xxv4
- Resolves: #1346045

* Tue Oct 4 2016 Petr Oros <poros@redhat.com> - 1:1.17-23
- Update microcode data file to 20160714 revision.
- Resolves: #1346045

* Wed Sep 14 2016 Petr Oros <poros@redhat.com> - 1:1.17-22
- Update amd microcode data file to amd-ucode-2013-11-07
- Resolves: #1322525

* Wed Nov 11 2015 Petr Oros <poros@redhat.com> - 1:1.17-21
- Update microcode data file to 20151106 revision.
- Resolves: #1244968
- Remove bad file permissions on /lib/udev/rules.d/89-microcode.rules
- Resolves: #1201276

* Thu Jan 29 2015 Petr Oros <poros@redhat.com> - 1:1.17-20
- Update microcode data file to 20150121 revision.
- Resolves: #1123992

* Mon Jun 30 2014 Petr Oros <poros@redhat.com> - 1:1.17-19
- Update microcode data file to 20140624 revision.
- Resolves: #1113394

* Mon May 05 2014 Petr Oros <poros@redhat.com> - 1:1.17-18
- Update microcode data file to 20140430 revision.
- Resolves: #1036240

* Mon Sep 09 2013 Anton Arapov <anton@redhat.com> - 1:1.17-17
- Update to microcode-20130906.dat
- Resolves: rhbz#1005606

* Mon Aug 26 2013 Anton Arapov <anton@redhat.com> - 1:1.17-16
- Microcode update should be skipped in virtualized environment
- Resolves: rhbz#1000317

* Thu Aug 08 2013 Anton Arapov <anton@redhat.com> - 1:1.17-15
- Update to microcode-20130808.dat
- Resolves: rhbz#915957

* Mon Oct 22 2012 Anton Arapov <anton@redhat.com> - 1:1.17-14
- Update microcode for AMD cpus to 2012-09-10
- Resolves: rhbz#867078

* Mon Sep 24 2012 Anton Arapov <anton@redhat.com> - 1:1.17-13
- Update to microcode-20120606v2.dat
- Resolves: rhbz#818096

* Mon Aug 27 2012 Anton Arapov <anton@redhat.com> - 1:1.17-12
- Fix udev rule
- Resolves: rhbz#740932
- Update to microcode-20120606.dat
- Resolves: rhbz#818096

* Fri Feb 17 2012 Anton Arapov <anton@redhat.com> - 1:1.17-11
- Update microcode for AMD cpus to 20120117
- Resolves: rhbz#787757

* Wed Feb 15 2012 Anton Arapov <anton@redhat.com> - 1:1.17-10
- Fix buffer overflow
- Resolves: rhbz#768803
- Update to microcode-20111110.dat
- Resolves: rhbz#736266

* Wed Oct 05 2011 Anton Arapov <anton@redhat.com> - 1:1.17-9
- Update to microcode-20110915.dat
- Resolves: rhbz#696582

* Thu Jul 21 2011 Anton Arapov <anton@redhat.com> - 1:1.17-8
- Revert: Minor fix of the udev rule
- Relates: rhbz#682668

* Wed Jul 20 2011 Anton Arapov <anton@redhat.com> - 1:1.17-7
- Minor fix of the udev rule
- Include microcode update for AMD cpus
- Resolves: rhbz#682668

* Wed Jul 20 2011 Anton Arapov <anton@redhat.com> - 1:1.17-6
- Update to microcode-20110428.dat
- Resolves: rhbz#696582

* Thu Mar 24 2011 Anton Arapov <anton@redhat.com> - 1:1.17-5
- fix memory leak.
- Resolves: rhbz#684009

* Wed Nov 24 2010 Anton Arapov <anton@redhat.com> - 1:1.17-4
- Update to microcode-20101123.dat
- Make microcode_ctl event driven
- Resolves: rhbz#578107

* Tue Feb 23 2010 Anton Arapov <anton@redhat.com> - 1:1.17-3
- Update to microcode-20100209.dat [488319]

* Fri Feb 19 2010 Kyle McMartin <kyle@redhat.com> - 1:1.17-2
- Don't use a CVS release for RHEL, otherwise it'll always be a branch
  and irritating.
- Fix syntax error in microcode_ctl.init.
- Resolves: rhbz#552246.

* Mon Nov 30 2009 Dennis Gregorovic <dgregor@redhat.com> - 1:1.17-1.41.1
- Rebuilt for RHEL 6

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

