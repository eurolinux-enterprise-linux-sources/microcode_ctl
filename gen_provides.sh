#! /bin/bash -efux

# Generator of RPM "Provides:" tags for Intel microcode files.
#
# SPDX-License-Identifier: CC0-1.0

IFS=$'\n'
UPDATED="intel-beta"
CODENAMES="codenames"

if [ "$#" -ge 1 ]; then
	CODENAMES="$1"
	shift
fi

# Match only FF-MM-SS ucode files under intel-ucode/intel-ucode-with-caveats
# directories.
for f in $(grep -E '/intel-ucode.*/[0-9a-f][0-9a-f]-[0-9a-f][0-9a-f]-[0-9a-f][0-9a-f]$'); do
	ucode=$(basename "$f")
	ucode_caveat="$(basename "$(dirname "$(dirname "$f")")")"
	ucode_fname="$ucode_caveat/$ucode"
	file_sz="$(stat -c "%s" "$f")"
	skip=0

	while :; do
		[ "$skip" -lt "$file_sz" ] || break

		# Microcode header format description:
		# https://gitlab.com/iucode-tool/iucode-tool/blob/master/intel_microcode.c
		IFS=' ' read hdrver rev \
		       date_y date_d date_m \
		       cpuid cksum ldrver \
		       pf_mask datasz totalsz <<- EOF
		$(dd if="$f" bs=1 skip="$skip" count=36 status=none \
			| hexdump -e '"" 1/4 "%u " 1/4 "%#x " \
			                 1/2 "%04x " 1/1 "%02x " 1/1 "%02x " \
					 1/4 "%08x " 1/4 "%x " 1/4 "%#x " \
					 1/4 "%u " 1/4 "%u " 1/4 "%u" "\n"')
		EOF

		[ 0 != "$datasz" ] || datasz=2000
		[ 0 != "$totalsz" ] || totalsz=2048

		# TODO: add some sanity/safety checks here.  As of now, there's
		#       a (pretty fragile) assumption that all the matched files
		#       are valid Intel microcode files in the expected format.

		skip=$((skip + totalsz))

		#[ -n "$rev" ] || continue

		# Basic "Provides:" tag. Everything else is bells and whistles.
		# It's possible that microcode files for different platform_id's
		# and the same CPUID have the same version, that's why "sort -u"
		# in the end.
		printf "firmware(intel-ucode/%s) = %s\n" "$ucode" "$rev"

		# Generate extended "Provides:" tags with additional
		# information, which allow more precise matching.
		printf "iucode_date(fname:%s;cpuid:%s;pf_mask:0x%x) = %s.%s.%s\n" \
			"$ucode_fname" "$cpuid" "$pf_mask" "$date_y" "$date_m" "$date_d"
		printf "iucode_rev(fname:%s;cpuid:%s;pf_mask:0x%x) = %s\n" \
			"$ucode_fname" "$cpuid" "$pf_mask" "$rev"

		# Generate tags for each possible platform_id
		_pf=1
		_pf_mask="$pf_mask"
		while [ 0 -lt "$_pf_mask" ]; do
			[ 1 -ne "$((_pf_mask % 2))" ] || \
				# We try to provide a more specific firmware()
				# dependency here.  It has incorrect file name,
				# but allows constructing a required RPM
				# capability name by (directly) using
				# the contents of /proc/cpuinfo and
				# /sys/devices/system/cpu/cpu*/microcode/processor_flags
				# (except for a Deschutes CPU with sig 0x1632)
				printf "iucode_rev(fname:%s;platform_id:0x%x) = %s\n" \
					"$ucode_fname" "$_pf" "$rev"

			_pf_mask=$((_pf_mask / 2))
			_pf=$((_pf * 2))
		done

		# Generate tags with codename information, in case
		# it is available
		cpuid_up="$(echo "$cpuid" | tr 'a-z' 'A-Z')"
		if [ -e "$CODENAMES" ]; then
			grep '	'"$cpuid_up"'	' "$CODENAMES" \
			| while IFS=$'\t' read segm int_fname codename stepping candidate_pf rest; do
				codename=$(echo "$codename" | tr ' (),' '_[];')
				candidate_pf=$(printf "%u" "0x${candidate_pf}")
				[ \( 0 -ne "$pf_mask" \) -a \
				  \( "$candidate_pf" -ne "$((candidate_pf & pf_mask))" \) ] || { \
					printf "iucode_rev(fname:%s;cpuid:%s;pf_mask:0x%x;segment:\"%s\";codename:\"%s\";stepping:\"%s\";pf_model:0x%x) = %s\n" \
						"$ucode_fname" "$cpuid" "$pf_mask" \
						"$segm" "$codename" "$stepping" "$candidate_pf" \
						"$rev";
					printf "iucode_date(fname:%s;cpuid:%s;pf_mask:0x%x;segment:\"%s\";codename:\"%s\";stepping:\"%s\";pf_model:0x%x) = %s.%s.%s\n" \
						"$ucode_fname" "$cpuid" "$pf_mask" \
						"$segm" "$codename" "$stepping" "$candidate_pf" \
						"$date_y" "$date_m" "$date_d";
				  }
			done
		fi

		# Kludge squared: generate additional "Provides:" tags
		# for the files in the overrides tarball (that a placed
		# in a separate caveat with a specific name)
		[ "x${ucode_caveat}" != "x${UPDATED}" ] || {
			printf "firmware_updated(intel-ucode/%s) = %s\n" \
				"$ucode" "$rev";
		}
	done
done | sort -u
