#!/usr/bin/python3
import apt
import gettext
import gi
import os
import platform
import subprocess
import locale
import cairo
import glob
import re
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio, Gdk, GdkPixbuf

NORUN_FLAG = os.path.expanduser("~/.linuxmint/mintwelcome/norun.flag")

# i18n
gettext.install("mintwelcome", "/usr/share/linuxmint/locale")
from locale import gettext as _
locale.bindtextdomain("mintwelcome", "/usr/share/linuxmint/locale")
locale.textdomain("mintwelcome")

LAYOUT_STYLE_LEGACY, LAYOUT_STYLE_NEW = range(2)

class SidebarRow(Gtk.ListBoxRow):

    def __init__(self, page_widget, page_name, icon_name):
        Gtk.ListBoxRow.__init__(self)
        self.page_widget = page_widget
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.set_border_width(6)
        image = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON)
        box.pack_start(image, False, False, 0)
        label = Gtk.Label()
        label.set_text(page_name)
        box.pack_start(label, False, False, 0)
        self.add(box)

class MintWelcome():

    def __init__(self):
        builder = Gtk.Builder()
        builder.set_translation_domain("mintwelcome")
        builder.add_from_file('/usr/share/linuxmint/mintwelcome/mintwelcome.ui')

        window = builder.get_object("main_window")
        window.set_icon_name("hamonikr-community")
        window.set_position(Gtk.WindowPosition.CENTER)
        window.connect("destroy", Gtk.main_quit)

        try:
            with open("/etc/hamonikr/info") as f:
                config = dict([line.strip().split("=", 1) for line in f if "=" in line])
            codename = config['CODENAME'].capitalize()
            edition = config['EDITION'].replace('"', '')
            release = config['RELEASE']
            desktop = config['DESKTOP']
            release_notes = config['RELEASE_NOTES_URL']
            new_features = config['NEW_FEATURES_URL']                
        except FileNotFoundError:
            try:
                with open("/etc/lsb-release") as f:
                    config = dict([line.strip().split("=", 1) for line in f if "=" in line])
                codename = config['DISTRIB_CODENAME'].capitalize()
                edition = config['DISTRIB_DESCRIPTION'].replace('"', '')
                release = config['DISTRIB_RELEASE']
                desktop = config['DISTRIB_ID']
                release_notes = "https://hamonikr.org"
                new_features = "https://github.com/hamonikr"
            except FileNotFoundError:
                print("Both /etc/hamonikr/info and /etc/lsb-release files are missing.")                
        except Exception as e:
            print(f"An unexpected error occurred: {e}")        

        architecture = "64-bit"
        if platform.machine() != "x86_64":
            architecture = "32-bit"

        # distro-specific
        with open("/etc/lsb-release") as f:
            config = dict([line.strip().split("=", 1) for line in f if "=" in line])
        dist_name = config['DISTRIB_ID']

        if os.path.exists("/usr/share/doc/debian-system-adjustments/copyright"):
            dist_name = "LMDE"

        # Setup the labels in the Mint badge
        builder.get_object("label_version").set_text("%s %s" % (dist_name, release))
        builder.get_object("label_edition").set_text("%s %s" % (edition, architecture))

        # Setup the main stack
        self.stack = Gtk.Stack()
        builder.get_object("center_box").pack_start(self.stack, True, True, 0)
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(150)

        # Action buttons
        builder.get_object("button_forums").connect("clicked", self.visit, "https://hamonikr.org")
        # builder.get_object("button_documentation").connect("clicked", self.visit, "https://hamonikr.org/board_manual")
        builder.get_object("button_contribute").connect("clicked", self.visit, "https://github.com/hamonikr")
        builder.get_object("button_irc").connect("clicked", self.visit, "https://hamonikr.org/how_join")
        builder.get_object("button_codecs").connect("clicked", self.visit, "apt://mint-meta-codecs?refresh=yes")
        builder.get_object("button_new_features").connect("clicked", self.visit, "https://docs.hamonikr.org/hamonikr-8.0#new_feature")
        builder.get_object("button_release_notes").connect("clicked", self.visit, "https://docs.hamonikr.org/hamonikr-8.0#release_note")
        builder.get_object("button_mintupdate").connect("clicked", self.launch, "mintupdate")
        builder.get_object("button_mintinstall").connect("clicked", self.launch, "mintinstall")
        builder.get_object("button_timeshift").connect("clicked", self.pkexec, "timeshift-gtk")
        builder.get_object("button_mintdrivers").connect("clicked", self.launch, "driver-manager")
        builder.get_object("button_gufw").connect("clicked", self.launch, "gufw")
        builder.get_object("button_layout_legacy").connect("clicked", self.on_button_layout_clicked, LAYOUT_STYLE_LEGACY)
        builder.get_object("button_layout_new").connect("clicked", self.on_button_layout_clicked, LAYOUT_STYLE_NEW)
        
        # custom new features
        builder.get_object("button_license").connect("clicked", self.visit, "https://docs.hamonikr.org/hamonikr-8.0/license")

        # custom recommended software
        builder.get_object("button_hancom").connect("clicked", self.launch, "hoffice-support")
        builder.get_object("button_v3lite").connect("clicked", self.visit, "apt://ahnlab-v3lite?refresh=yes")
        builder.get_object("button_site_compatibility_support").connect("clicked", self.launch, "site-compatibility-support")
        builder.get_object("button_kakaotalk").connect("clicked", self.launch, "/usr/lib/linuxmint/mintwelcome/kakaotalk-install")
        builder.get_object("kakaotalk_install_guide").connect("clicked", self.on_button_kakaotalk_install_guide)
        builder.get_object("button_battlenet").connect("clicked", self.launch, "/usr/lib/linuxmint/mintwelcome/battlenet-install")
        builder.get_object("battlenet_install_guide").connect("clicked", self.on_button_battlenet_install_guide)
        builder.get_object("button_lol").connect("clicked", self.launch, "/usr/lib/linuxmint/mintwelcome/lol-install")
        builder.get_object("lol_install_guide").connect("clicked", self.on_button_lol_install_guide)
        builder.get_object("button_ventoy").connect("clicked", self.visit, "apt://ventoy?refresh=yes")
        builder.get_object("button_systemback").connect("clicked", self.visit, "apt://systemback?refresh=yes")
        builder.get_object("button_live_usb_creator").connect("clicked", self.visit, "apt://live-usb-creator?refresh=yes")
        builder.get_object("button_hamonikr_drive").connect("clicked", self.visit, "https://drive.hamonikr.org/")
        builder.get_object("button_lutris").connect("clicked", self.on_button_lutris_clicked)
        builder.get_object("button_kodi").connect("clicked", self.on_button_kodi_clicked)
        builder.get_object("button_korean_language").connect("clicked", self.on_button_korean_language)

        
        

        ### ---------- development software start ---------- ###
        
        # Editor
        # builder.get_object("button_vscode").connect("clicked", self.visit, "apt://code?refresh=yes")
        builder.get_object("button_vscode").connect("clicked", self.on_button_vscode_clicked)

        # DBMS
        builder.get_object("button_mysql_server").connect("clicked", self.visit, "apt://mysql-server?refresh=yes")
        builder.get_object("button_postgresql").connect("clicked", self.visit, "apt://postgresql?refresh=yes")

        # WEB/WAS
        builder.get_object("button_apache").connect("clicked", self.visit, "apt://apache2?refresh=yes")
        builder.get_object("button_tomcat").connect("clicked", self.visit, "apt://tomcat9?refresh=yes")

        # Development Language
        builder.get_object("button_default_jdk").connect("clicked", self.visit, "apt://default-jdk?refresh=yes")
        builder.get_object("button_python_pip").connect("clicked", self.visit, "apt://python3-pip?refresh=yes")

        # Etc...
        builder.get_object("button_asbru").connect("clicked", self.visit, "apt://asbru-cm?refresh=yes")
        builder.get_object("button_git").connect("clicked", self.visit, "apt://git?refresh=yes")
        builder.get_object("button_rabbitvcs").connect("clicked", self.visit, "apt://hamonikr-nemo-rabbitvcs?refresh=yes")
        builder.get_object("button_avahi").connect("clicked", self.visit, "apt://hamonikr-avahi-service?refresh=yes")

        ### ---------- development software end ---------- ###

        # custom help
        builder.get_object("button_help").connect("clicked", self.visit, "https://docs.hamonikr.org/hamonikr-8.0")
        builder.get_object("button_shortcut").connect("clicked", self.launch, "conky-shortcut-on-off")
        # builder.get_object("button_hamonikr_cli_tools").connect("clicked", self.visit, "apt://hamonikr-cli-tools?refresh=yes")

        # Settings button depends on DE
        de_is_cinnamon = False
        self.theme = None
        if os.getenv("XDG_CURRENT_DESKTOP") in ["Cinnamon", "X-Cinnamon"]:
            builder.get_object("button_settings").connect("clicked", self.launch, "cinnamon-settings")
            de_is_cinnamon = True
            self.theme = Gio.Settings(schema="org.cinnamon.desktop.interface").get_string("gtk-theme")
        elif os.getenv("XDG_CURRENT_DESKTOP") == "MATE":
            builder.get_object("button_settings").connect("clicked", self.launch, "mate-control-center")
        elif os.getenv("XDG_CURRENT_DESKTOP") == "XFCE":
            builder.get_object("button_settings").connect("clicked", self.launch, "xfce4-settings-manager")
        else:
            # Hide settings
            builder.get_object("box_first_steps").remove(builder.get_object("box_settings"))

        # Hide Desktop colors
        builder.get_object("box_first_steps").remove(builder.get_object("box_colors"))

        # Hide Cinnamon layout settings in other DEs
        if not de_is_cinnamon:
            builder.get_object("box_first_steps").remove(builder.get_object("box_cinnamon"))

        # Hide codecs box if they're already installed
        add_codecs = False
        cache = apt.Cache()
        if "mint-meta-codecs" in cache:
            pkg = cache["mint-meta-codecs"]
            if not pkg.is_installed:
                add_codecs = True
        if not add_codecs:
            builder.get_object("box_first_steps").remove(builder.get_object("box_codecs"))

        # Hide drivers if mintdrivers is absent (LMDE)
        if not os.path.exists("/usr/bin/mintdrivers"):
            builder.get_object("box_first_steps").remove(builder.get_object("box_drivers"))

        # Hide new features page for LMDE
        if dist_name == "LMDE":
            builder.get_object("box_documentation").remove(builder.get_object("box_new_features"))

        # Hide for Ubuntu
        if dist_name == "Ubuntu":
            builder.get_object("box_first_steps").remove(builder.get_object("box_drivers"))
            builder.get_object("box_first_steps").remove(builder.get_object("box_timeshift"))            
            builder.get_object("box_first_steps").remove(builder.get_object("box_drivers"))            
            builder.get_object("box_first_steps").remove(builder.get_object("box_codecs"))            
            builder.get_object("box_first_steps").remove(builder.get_object("box_updatemanager"))
            builder.get_object("box_first_steps").remove(builder.get_object("box_softwarecenter"))
            builder.get_object("box_first_steps").remove(builder.get_object("box_gufw"))
            builder.get_object("box_help").remove(builder.get_object("box_hamonikrshortcut"))
            builder.get_object("box_home").remove(builder.get_object("box_hamonikrlogo"))
            builder.get_object("box_documentation").remove(builder.get_object("box_new_features"))
            builder.get_object("box_documentation").remove(builder.get_object("box_releasenote"))
            builder.get_object("box_documentation").remove(builder.get_object("box_pkglicense"))            
            builder.get_object("box_second_steps").remove(builder.get_object("box_install_hoffice"))            
            builder.get_object("box_second_steps").remove(builder.get_object("box_install_webplugin"))            
            builder.get_object("box_second_steps").remove(builder.get_object("box_install_hamonikrdrive"))            
            # builder.get_object("box_second_steps").remove(builder.get_object("box_install_lutris"))            
            builder.get_object("box_second_steps").remove(builder.get_object("box_install_kodi"))     
        else:
            # 하모니카 OS 라도 7.0 이후부터 아래 패키지 중지
            # hoffice
            builder.get_object("box_second_steps").remove(builder.get_object("box_install_hoffice"))
            # Hide 사이트 호환성 패키지
            builder.get_object("box_second_steps").remove(builder.get_object("box_install_webplugin"))
            # Hide hamonikr-drive
            builder.get_object("box_second_steps").remove(builder.get_object("box_install_hamonikrdrive")) 
            builder.get_object("button_shortcut").connect("clicked", self.launch, "conky-shortcut-on-off")
            # Hide kodi
            # builder.get_object("box_second_steps").remove(builder.get_object("box_install_kodi"))
            # Hide lutris
            # builder.get_object("box_second_steps").remove(builder.get_object("box_install_lutris"))
            builder.get_object("box_second_steps").remove(builder.get_object("box_install_ventoy"))                     

        # Construct the stack switcher
        list_box = builder.get_object("list_navigation")

        page = builder.get_object("page_home")
        self.stack.add_named(page, "page_home")
        list_box.add(SidebarRow(page, _("Welcome"), "go-home-symbolic"))
        self.stack.set_visible_child(page)

        page = builder.get_object("page_first_steps")
        self.stack.add_named(page, "page_first_steps")
        list_box.add(SidebarRow(page, _("HamoniKR Settings"), "dialog-information-symbolic"))
        
        page = builder.get_object("page_second_steps")
        self.stack.add_named(page, "page_second_steps")
        list_box.add(SidebarRow(page, _("Recommended Program"), "dialog-information-symbolic"))

        page = builder.get_object("page_third_steps")
        self.stack.add_named(page, "page_third_steps")
        list_box.add(SidebarRow(page, _("Development Program"), "dialog-information-symbolic"))

        page = builder.get_object("page_help")
        self.stack.add_named(page, "page_help")
        list_box.add(SidebarRow(page, _("Help"), "help-browser-symbolic"))

        page = builder.get_object("page_new_feature")
        self.stack.add_named(page, "page_new_feature")
        list_box.add(SidebarRow(page, _("HamoniKR Information"), "accessories-dictionary-symbolic"))

        list_box.connect("row-activated", self.sidebar_row_selected_cb)

        # Construct the bottom toolbar
        box = builder.get_object("toolbar_bottom")
        checkbox = Gtk.CheckButton()
        checkbox.set_label(_("Show this dialog at startup"))
        if not os.path.exists(NORUN_FLAG):
            checkbox.set_active(True)
        checkbox.connect("toggled", self.on_button_toggled)
        box.pack_end(checkbox)

        scale = window.get_scale_factor()

        self.color = "green"
        self.dark_mode = False

        # Use HIDPI pictures if appropriate
        if scale == 1:
            surface = self.surface_for_path("/usr/share/linuxmint/mintwelcome/hamonikr_legacy.png", scale)
            builder.get_object("img_legacy").set_from_surface(surface)
            surface = self.surface_for_path("/usr/share/linuxmint/mintwelcome/hamonikr_modern.png", scale)
            builder.get_object("img_modern").set_from_surface(surface)
        else:
            surface = self.surface_for_path("/usr/share/linuxmint/mintwelcome/hamonikr_legacy.png", scale)
            builder.get_object("img_legacy").set_from_surface(surface)
            surface = self.surface_for_path("/usr/share/linuxmint/mintwelcome/hamonikr_modern.png", scale)
            builder.get_object("img_modern").set_from_surface(surface)

        # if dist_name != "Ubuntu":
        #     path = "/usr/share/linuxmint/mintwelcome/colors/"
        #     if scale == 2:
        #         path = "/usr/share/linuxmint/mintwelcome/colors/hidpi/"
        #     for color in ["green", "aqua", "blue", "brown", "grey", "orange", "pink", "purple", "red", "sand", "teal"]:
        #         builder.get_object("img_" + color).set_from_surface(self.surface_for_path("%s/%s.png" % (path, color), scale))
        #         builder.get_object("button_" + color).connect("clicked", self.on_color_button_clicked, color)

        builder.get_object("switch_dark").connect("state-set", self.on_dark_mode_changed)

        window.set_default_size(800, 500)
        window.show_all()

    def surface_for_path(self, path, scale):
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)

        return Gdk.cairo_surface_create_from_pixbuf(pixbuf, scale)

    def sidebar_row_selected_cb(self, list_box, row):
        self.stack.set_visible_child(row.page_widget)

    def on_button_toggled(self, button):
        if button.get_active():
            if os.path.exists(NORUN_FLAG):
                os.system("rm -rf %s" % NORUN_FLAG)
        else:
            os.system("mkdir -p ~/.linuxmint/mintwelcome")
            os.system("touch %s" % NORUN_FLAG)

    def on_button_layout_clicked (self, button, style):

        # settings = Gio.Settings("org.cinnamon")
        # settings2 = Gio.Settings("org.cinnamon.desktop.interface")
        # settings3 = Gio.Settings("org.cinnamon.desktop.wm.preferences")
        # settings4 = Gio.Settings("org.cinnamon.theme")
        # settings5 = Gio.Settings("org.nemo.desktop")
        # settings6 = Gio.Settings("org.gnome.desktop.interface")
        # settings7 = Gio.Settings("org.cinnamon.desktop.background")
        # settings8 = Gio.Settings("org.gnome.desktop.background")
        # settings9 = Gio.Settings("org.mate.background")
        # settings10 = Gio.Settings("x.dm.slick-greeter")

        # applets_legacy = ['panel1:left:0:menu@cinnamon.org',
        #                   'panel1:left:1:show-desktop@cinnamon.org',
        #                   'panel1:left:2:panel-launchers@cinnamon.org',
        #                   'panel1:left:3:window-list@cinnamon.org',
        #                   'panel1:right:0:systray@cinnamon.org',
        #                   'panel1:right:1:xapp-status@cinnamon.org',
        #                   'panel1:right:2:keyboard@cinnamon.org',
        #                   'panel1:right:3:notifications@cinnamon.org',
        #                   'panel1:right:4:printers@cinnamon.org',
        #                   'panel1:right:5:removable-drives@cinnamon.org',
        #                   'panel1:right:6:user@cinnamon.org',
        #                   'panel1:right:7:network@cinnamon.org',
        #                   'panel1:right:8:sound@cinnamon.org',
        #                   'panel1:right:9:power@cinnamon.org',
        #                   'panel1:right:10:calendar@cinnamon.org']

        # applets_new = ['panel1:left:0:menu@cinnamon.org:0', 
        #                'panel1:left:1:grouped-window-list@cinnamon.org:1', 
        #                'panel1:right:0:scale@cinnamon.org:2', 
        #                'panel1:right:1:expo@cinnamon.org:3', 
        #                'panel1:right:3:systray@cinnamon.org:5', 
        #                'panel1:right:4:notifications@cinnamon.org:6', 
        #                'panel1:right:5:printers@cinnamon.org:7', 
        #                'panel1:right:6:removable-drives@cinnamon.org:8', 
        #                'panel1:right:8:bluetooth@cinnamon.org:10', 
        #                'panel1:right:9:network@cinnamon.org:11', 
        #                'panel1:right:10:sound@cinnamon.org:12', 
        #                'panel1:right:11:power@cinnamon.org:13', 
        #                'panel1:right:12:calendar@cinnamon.org:14',
        #                'panel1:right:13:weather@mockturtl:15', 
        #                'panel1:right:14:show-desktop@cinnamon.org:16', 
        #                'panel1:right:15:user@cinnamon.org:17']

        if style == LAYOUT_STYLE_LEGACY:

            # 전통적인 윈도우 테마 (hamonikr-themes 종속적)
            os.system(" rm -rf ~/.hamonikr/theme")
            os.system("hamonikr-theme-setting winstyle")

            # # 패널 위치
            # settings.set_strv("panels-enabled", ['1:0:bottom'])

            # # 테마설정(아이콘, 컨트롤, 창테두리)
            # settings2.set_string("icon-theme", "HamoniKR")
            # settings2.set_string("gtk-theme", "HamoniKR")
            # settings3.set_string("theme", "HamoniKR")
            # settings4.set_string("name", "HamoniKR")

            # # 바탕화면, greeter 배경화면
            # settings7.set_string("picture-uri", "file:////usr/share/backgrounds/hamonikr/default_background.jpg")
            # settings8.set_string("picture-uri", "file:////usr/share/backgrounds/hamonikr/default_background.jpg")
            # settings9.set_string("picture-filename", "file:////usr/share/backgrounds/hamonikr/default_background.jpg")
            # settings10.set_string("background", "file:////usr/share/backgrounds/hamonikr/default_background.jpg")

        elif style == LAYOUT_STYLE_NEW:
            
            # 패널이 상단에 있는 윈도우 테마 (hamonikr-themes 종속적)
            os.system(" rm -rf ~/.hamonikr/theme")            
            os.system("hamonikr-theme-setting macstyle")

            # # 패널위치
            # settings.set_strv("panels-enabled", ['1:0:top'])
            
            # # 테마설정(아이콘, 컨트롤, 창테두리)
            # settings2.set_string("icon-theme", "HamoniKR")
            # settings2.set_string("gtk-theme", "HamoniKR-light")
            # settings3.set_string("theme", "HamoniKR-light")
            # settings4.set_string("name", "HamoniKR-dark")

            # # 바탕화면, greeter 배경화면
            # settings7.set_string("picture-uri", "file:////usr/share/backgrounds/hamonikr/bg4.jpg")
            # settings8.set_string("picture-uri", "file:////usr/share/backgrounds/hamonikr/bg4.jpg")
            # settings9.set_string("picture-filename", "file:////usr/share/backgrounds/hamonikr/bg4.jpg")
            # settings10.set_string("background", "file:////usr/share/backgrounds/hamonikr/bg4.jpg")

        # applets = applets_new
        # left_icon_size = 24
        # center_icon_size = 24
        # right_icon_size = 16
        # panel_size = 33
        # menu_label = ""

        # ## 패널크기
        # settings.set_strv("panels-height", ['1:%s' % panel_size])
        # settings.set_strv("enabled-applets", applets)
        # settings.set_string("app-menu-label", menu_label)
        # settings.set_string("panel-zone-icon-sizes", "[{\"panelId\": 1, \"left\": %s, \"center\": %s, \"right\": %s}]" % (left_icon_size, center_icon_size, right_icon_size))
        # settings.set_string("panel-zone-symbolic-icon-sizes", "[{\"panelId\": 1, \"left\": %s, \"center\": %s, \"right\": %s}]" % (left_icon_size, center_icon_size, right_icon_size))

        # ## 폰트설정
        # settings2.set_string("font-name", "나눔스퀘어라운드 10")
        # settings3.set_string("titlebar-font", "나눔스퀘어라운드 Bold 10")
        # settings5.set_string("font", "나눔스퀘어라운드 10")
        # settings6.set_string("document-font-name", "나눔스퀘어라운드 10")
        # settings6.set_string("monospace-font-name", "Droid Sans Mono 10")
        

        os.system("cinnamon --replace &")

    def on_dark_mode_changed(self, button, state):
        self.dark_mode = state
        self.change_color()

    def on_color_button_clicked(self, button, color):
        self.color = color
        self.change_color()

    def change_color(self):
        theme = "Mint-Y"
        wm_theme = "Mint-Y"
        cinnamon_theme = "Mint-Y-Dark"
        if self.dark_mode:
            theme = "%s-Dark" % theme
            wm_theme = "Mint-Y-Dark"
        if self.color != "green":
            theme = "%s-%s" % (theme, self.color.title())
            cinnamon_theme = "Mint-Y-Dark-%s" % self.color.title()

        if os.getenv("XDG_CURRENT_DESKTOP") in ["Cinnamon", "X-Cinnamon"]:
            settings = Gio.Settings(schema="org.cinnamon.desktop.interface")
            settings.set_string("gtk-theme", theme)
            settings.set_string("icon-theme", theme)
            Gio.Settings(schema="org.cinnamon.desktop.wm.preferences").set_string("theme", wm_theme)
            Gio.Settings(schema="org.cinnamon.theme").set_string("name", cinnamon_theme)
        elif os.getenv("XDG_CURRENT_DESKTOP") == "MATE":
            settings = Gio.Settings(schema="org.mate.interface")
            settings.set_string("gtk-theme", theme)
            settings.set_string("icon-theme", theme)
            Gio.Settings(schema="org.mate.Marco.general").set_string("theme", wm_theme)
        elif os.getenv("XDG_CURRENT_DESKTOP") == "XFCE":
            subprocess.call(["xfconf-query", "-c", "xsettings", "-p", "/Net/ThemeName", "-s", theme])
            subprocess.call(["xfconf-query", "-c", "xsettings", "-p", "/Net/IconThemeName", "-s", theme])
            subprocess.call(["xfconf-query", "-c", "xfwm4", "-p", "/general/theme", "-s", theme])

    def visit(self, button, url):
        subprocess.Popen(["xdg-open", url])

    def launch(self, button, command):
        subprocess.Popen([command])

    def launch2(self, button, command, command2):
        subprocess.Popen([command, command2])

    def pkexec(self, button, command):
        subprocess.Popen(["pkexec", command])

    def on_button_lutris_clicked (self, button):
        
        # Lutris가 설치되어 있는지 확인
        is_installed = os.system("dpkg-query -W -f='${Status}' lutris 2>/dev/null | grep -q 'ok installed'")
        
        # Lutris가 설치되어 있지 않은 경우에만 설치 명령을 실행
        if is_installed != 0:
            # os.system("pkexec sh -c 'add-apt-repository -y ppa:lutris-team/lutris && apt update && apt install -y lutris'")
            os.system("gnome-terminal -- bash -c \"pkexec sh -c 'add-apt-repository -y ppa:lutris-team/lutris 2>/dev/null && apt update && apt install -y lutris'\"")
        else:
            os.system("lutris &")

    def on_button_vscode_clicked (self, button):
        is_installed = os.system("dpkg-query -W -f='${Status}' code 2>/dev/null | grep -q 'ok installed'")
        
        if is_installed != 0:
            # os.system("pkexec sh -c 'wget -q https://packages.microsoft.com/keys/microsoft.asc -O- | apt-key add - && echo \"deb [arch=amd64] https://packages.microsoft.com/repos/vscode stable main\" > /etc/apt/sources.list.d/vscode.list' && apt install -y code")
            os.system("gnome-terminal -- bash -c \"pkexec sh -c 'wget -q https://packages.microsoft.com/keys/microsoft.asc -O- | apt-key add - && echo \"deb [arch=amd64] https://packages.microsoft.com/repos/vscode stable main\" > /etc/apt/sources.list.d/vscode.list' && apt install -y code'\"")
        else:
            os.system("code &")

    def on_button_kodi_clicked (self, button):
        is_installed = os.system("dpkg-query -W -f='${Status}' kodi 2>/dev/null | grep -q 'ok installed'")
        
        if is_installed != 0:
            # os.system("pkexec sh -c 'add-apt-repository -y ppa:team-xbmc/ppa && apt update -y && apt install -y kodi'")
            os.system("gnome-terminal -- bash -c \"pkexec sh -c 'add-apt-repository -y ppa:team-xbmc/ppa && apt update -y && apt install -y kodi'\"")

        else:
            os.system("kodi &")

    def on_button_korean_language (self, button):
        os.system("sh -c /usr/lib/linuxmint/mintwelcome/kodi_korean_support")

    def on_button_kakaotalk_install_guide (self, button):
            os.system("xdg-open 'https://docs.hamonikr.org/hamonikr-8.0/key-features/hamonikr-welcome/kakaotalk'")
            
    def on_button_battlenet_install_guide (self, button):
            os.system("xdg-open 'https://docs.hamonikr.org/hamonikr-8.0/key-features/game/battlenet'")

    def on_button_lol_install_guide (self, button):
            os.system("xdg-open 'https://docs.hamonikr.org/hamonikr-8.0/key-features/game/lol'")

if __name__ == "__main__":
    MintWelcome()
    Gtk.main()
