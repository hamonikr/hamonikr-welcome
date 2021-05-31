all: buildmo

buildmo:
	@echo "Building the mo files"
	# WARNING: the second sed below will only works correctly with the languages that don't contain "-"
	for file in `ls po/*.po`; do \
		lang=`echo $$file | sed 's@po/@@' | sed 's/.po//' | sed 's/mintwelcome-//'`; \
		install -d usr/share/linuxmint/locale/$$lang/LC_MESSAGES/; \
		msgfmt -o usr/share/linuxmint/locale/$$lang/LC_MESSAGES/mintwelcome.mo $$file; \
	done \

clean:
	rm -rf usr/share/linuxmint/locale
