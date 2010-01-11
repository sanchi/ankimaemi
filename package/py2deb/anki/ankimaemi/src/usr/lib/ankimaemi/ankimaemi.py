#!/usr/bin/env python2.5
#
# ankimaemi - (c) 2009 Stefan Sayer
# based on ankimini by Damien Elmes
#
# see http://ichi2.net/anki/ and http://anki.garage.maemo.org 
#
# License: GPLv3
#
# sorry this code is so messy....its just hacked up....

appname = "ankimaemi"
appversion = "0.0.8"

import os
os.environ["SDL_VIDEO_X11_WMCLASS"]=appname
import osso

osso_c = osso.Context(appname, appversion, False)

import gtkhtml2
import gtk
import hildon

import time, cgi, sys, os, re, subprocess
from anki import DeckStorage as ds
from anki.sync import SyncClient, HttpSyncServerProxy
from anki.media import mediaRefs
from anki.utils import parseTags, joinTags

from gnome import gconf

def request_object(*args):
    print 'request object', args

gtk.set_application_name(appname)

class AnkiMiniApp(hildon.Program):

    currentCard = None
    deck = None
    played = False

    conf_client = None

    DECK_PATH = ""
    SYNC_USERNAME = ""
    SYNC_PASSWORD = ""

    recent_decks = []
    recent_sub_menu = None

    card_font_size = 30
    redraw_func = None

    def __init__(self):
        hildon.Program.__init__(self)

        self.window = hildon.Window()
        self.window.connect("destroy", self.quit_save)
        self.window.connect("delete_event", self.quit_save)
        self.window.connect("key-press-event", self.on_key_press)
        self.window.connect("window-state-event", self.on_window_state_change)
        self.window_in_fullscreen = False 
        self.window.set_title("")

        self.add_window(self.window)
        self.mainbox = gtk.VBox(False, 0)
        self.window.add(self.mainbox)

        self.statsbox = gtk.HBox(False, 0)
        self.mainbox.pack_start(self.statsbox, False, True, 0)

        self.statslabel = gtk.Label()
        self.statslabel.set_markup("T: 0/0 (0.0%) A: <b>0.0%</b>. ETA: <b>Unknown</b>")
        self.statsbox.pack_start(self.statslabel, True, True, 0)
        self.statslabel.show()

        self.missinglabel = gtk.Label()
        self.missinglabel.set_markup('<span foreground="red">0</span>+0+<span foreground="blue">0</span>')
        self.statsbox.pack_end(self.missinglabel, True, True, 0)
        self.missinglabel.show()

        self.statsbox.show()

        self.opbuttonsbox = gtk.HBox(False, 30)
        self.opbuttonsbox.set_size_request(400, 35)
        self.mainbox.pack_start(self.opbuttonsbox, False, False, 0)

        self.savebutton = gtk.Button()
        self.savebutton.connect("clicked", self.opbutclick, "save")
        self.savebuttonlabel = gtk.Label("save")
        self.savebuttonlabel.set_use_markup(True)
        self.savebuttonlabel.set_markup("save")
        self.savebutton.add(self.savebuttonlabel)
        self.savebuttonlabel.show()
        self.savebutton.show()
        self.opbuttonsbox.pack_start(self.savebutton, True, True, 0)

        self.markbutton = gtk.Button()
        self.markbutton.connect("clicked", self.opbutclick, "mark")
        self.markbuttonlabel = gtk.Label("mark")
        self.markbuttonlabel.set_use_markup(True)
        self.markbuttonlabel.set_markup("save")
        self.markbutton.add(self.markbuttonlabel)
        self.markbuttonlabel.show()

        self.opbuttonsbox.pack_start(self.markbutton, True, True, 0)
        self.markbutton.show()

        self.replaybutton = gtk.Button("replay")
        self.replaybutton.connect("clicked", self.opbutclick, "replay")
        self.opbuttonsbox.pack_start(self.replaybutton, True, True, 0)
        self.replaybutton.show()

        self.syncbutton = gtk.Button("sync")
        self.syncbutton.connect("clicked", self.opbutclick, "sync")
        self.opbuttonsbox.pack_start(self.syncbutton, True, True, 0)
        self.syncbutton.show()

        self.opbuttonsbox.show()

        self.qabox = gtk.VBox(False, 0)
        self.qabox.set_size_request(800, 250)
        self.mainbox.pack_start(self.qabox, True, True, 0)

        self.document = gtkhtml2.Document()
#    self.document.connect('request_url', request_url)
#    self.document.connect('link_clicked', link_clicked)

        self.view = gtkhtml2.View()
        self.set_html_doc('<center><div class="a"><br/><br/><br/>%s %s<br/><br/>Welcome.</div></center>' % 
                          (appname, appversion))
        self.view.connect('request_object', request_object)
        self.qabox.pack_start(self.view, True, True, 0)

        self.qabox.show()

        self.answerbuttonbox = gtk.HBox(False, 0)
        self.answerbuttonbox.set_size_request(800, 80)
        self.mainbox.pack_end(self.answerbuttonbox, False, True, 0)

        self.answerbutton = gtk.Button("Answer")
        self.answerbutton.connect("clicked", self.opbutclick, "answer")
        self.answerbuttonbox.pack_start(self.answerbutton, True, True, 0)
        self.answerbutton.show()

        self.answerbuttonbox.show()

        self.learnmorebox = gtk.HBox(False, 0)
        self.learnmorebox.set_size_request(800, 35)
        self.mainbox.pack_end(self.learnmorebox, False, True, 0)

        self.learnmorebutton = gtk.Button("Learn more")
        self.learnmorebutton.connect("clicked", self.opbutclick, "learnmore")
        self.learnmorebox.pack_start(self.learnmorebutton, True, True, 0)
        self.learnmorebutton.show()

        self.reviewearlybutton = gtk.Button("Review early")
        self.reviewearlybutton.connect("clicked", self.opbutclick, "reviewearly")
        self.learnmorebox.pack_start(self.reviewearlybutton, True, True, 0)
        self.reviewearlybutton.show()

        self.resultbuttonbox = gtk.HBox(False, 15)
        self.resultbuttonbox.set_size_request(800, 80)
        self.mainbox.pack_end(self.resultbuttonbox, False, True, 0)

        self.resbuttons = []
        for i in range(4):
            if i <> 0:
                but = gtk.Button(str(i))
            else: 
                but = gtk.Button("Soon")
            but.connect("clicked", self.resclick, str(i+1))
            self.resultbuttonbox.pack_start(but, True, True, 0)
            but.show()
            self.resbuttons.append(but)

        self.resultbuttonbox.show()

        self.mainbox.show()

        self.menu = gtk.Menu()
        menu_item = gtk.MenuItem("Open...")
        menu_item.connect("activate", self.choose_deck, "choose_deck")
        menu_item.show()

        menuItemRecent = gtk.MenuItem("Recent Decks")
        self.recent_sub_menu = gtk.Menu()
        menuItemRecent.set_submenu(self.recent_sub_menu)
        self.recent_sub_menu.show()

        menuItemSave = gtk.MenuItem("Save")
        menuItemSave.connect("activate", self.opbutclick, "save")

        menuItemClose = gtk.MenuItem("Close")
        menuItemClose.connect("activate", self.opbutclick, "close")

        menuItemSync = gtk.MenuItem("Sync")
        menuItemSync.connect("activate", self.opbutclick, "sync")

        menuItemSyncSettings = gtk.MenuItem("Sync account...")
        menuItemSyncSettings.connect("activate", self.run_settings, "run_settings")

        menuItemSeparator1 = gtk.SeparatorMenuItem()
        menuItemSeparator = gtk.SeparatorMenuItem()

        menuItemExit = gtk.MenuItem("Exit")
        menuItemExit.connect("activate", self.quit_save, "quit")

        self.menu.append(menu_item)
        self.menu.append(menuItemRecent)
        self.menu.append(menuItemSave)
        self.menu.append(menuItemSync)
        self.menu.append(menuItemClose)
        self.menu.append(menuItemSeparator)
        self.menu.append(menuItemSyncSettings)
        self.menu.append(menuItemSeparator1)
        self.menu.append(menuItemExit)
        self.window.set_menu(self.menu)

    def set_window_empty(self):
        self.opbuttonsbox.hide()
        self.answerbuttonbox.hide()
        self.resultbuttonbox.hide()

    def update_recent_menu(self, new_deckname):
        if new_deckname == "":
            return

        if self.recent_decks.count(new_deckname) > 0:
            self.recent_decks.remove(new_deckname)
        self.recent_decks = [new_deckname] + self.recent_decks
        self.recent_decks = self.recent_decks[0:5]

        self.set_recent_menu()

    def set_recent_menu(self):
        for i in range(5):
            if len(self.recent_decks) > i and self.recent_decks[i]:
                self.conf_client.set_string("/apps/anki/general/deck_path_history%d"%i, self.recent_decks[i])

        for child in self.recent_sub_menu.get_children():
            self.recent_sub_menu.remove(child)

        for deckname in self.recent_decks:
            menu_item_recent = gtk.MenuItem(deckname)
            menu_item_recent.connect("activate", self.recentclick, deckname)
            menu_item_recent.show()
            self.recent_sub_menu.add(menu_item_recent)

#        for f in range(5):
#            self.recent_decks[f].get_children()[0].set_markup(self.recent_decks_files[f])

    def init_deck(self):
        print "open deck.. " + self.DECK_PATH
        if not os.path.exists(self.DECK_PATH):
            self.err_dlg("Couldn't find your deck. Sorry.")
            return False
        try:
            self.deck = ds.Deck(self.DECK_PATH, backup=False)
            self.deck.rebuildQueue()
        except:
            self.err_dlg("Couldn't open your deck. Sorry.")
            return False
        return True

    def yesno_dlg(self, dtype, msg):
        dlg = gtk.MessageDialog(None,0, dtype, gtk.BUTTONS_YES_NO, msg)
        rep = dlg.run()
        dlg.destroy()
        while (gtk.events_pending()):
             gtk.main_iteration()

        return rep == gtk.RESPONSE_YES

    def choose_deck(self, widget, event):
        if self.deck:
            if self.deck.modifiedSinceSave() and self.yesno_dlg(gtk.MESSAGE_QUESTION, "Save the current deck first?"):
                self.deck_save()

        selector=hildon.FileChooserDialog(self.window,gtk.FILE_CHOOSER_ACTION_OPEN)
        rep=selector.run()
        selector.hide()
        a=selector.get_filename()
        selector.destroy()
        while (gtk.events_pending()):
             gtk.main_iteration()
        if rep==gtk.RESPONSE_OK:
            self.replace_deck_with_file(a)

    def run(self):
        self.window.show_all()

        self.conf_client = gconf.client_get_default()
        self.conf_client.add_dir("/apps/anki/general", gconf.CLIENT_PRELOAD_NONE)
        self.DECK_PATH = self.conf_client.get_string("/apps/anki/general/deck_path")
        self.SYNC_USERNAME = self.conf_client.get_string("/apps/anki/general/sync_username")
        self.SYNC_PASSWORD = self.conf_client.get_string("/apps/anki/general/sync_password")

        for i in range(5):
            h = self.conf_client.get_string("/apps/anki/general/deck_path_history%d"%i)
            if h:
                self.recent_decks.append(h)
        self.set_recent_menu()

        if not self.DECK_PATH or self.DECK_PATH == "": 
            self.set_window_empty()
        else:
            if self.init_deck():
                self.set_question()
                self.set_stats()
        gtk.main()

    def set_stats(self):
        s = self.deck.getStats()
        stats = (("T: %(dYesTotal)d/%(dTotal)d "
                  "(%(dYesTotal%)3.1f%%) "
                  "A: <b>%(gMatureYes%)3.1f%%</b>. ETA: <b>%(timeLeft)s</b>") % s)
        f = '<span color="#990000">%(failed)d</span>'
        r = '<span color="#000000">%(rev)d</span>'
        n = '<span color="#0000ff">%(new)d</span>'
        if self.currentCard:
            if self.currentCard.reps:
                if self.currentCard.successive:
                    r = "<u>" + r + "</u>"
                else:
                    f = "<u>" + f + "</u>"
            else:
                n = "<u>" + n + "</u>"

        stats2 = ('%s+%s+%s' % (f,r,n)) % s
        self.statslabel.set_markup(stats)
        self.missinglabel.set_markup(stats2)

    def on_window_state_change(self, widget, event, *args):
        if event.new_window_state & gtk.gdk.WINDOW_STATE_FULLSCREEN:
            self.window_in_fullscreen = True
        else:
            self.window_in_fullscreen = False

    def on_key_press(self, widget, event, *args):
        if event.keyval == gtk.keysyms.F6:
            # The "Full screen" hardware key has been pressed
            if self.window_in_fullscreen:
                self.window.unfullscreen ()
            else:
                self.window.fullscreen ()
	# zoom in
	elif event.keyval == gtk.keysyms.F7:
		self.card_font_size += 3
		if self.redraw_func:
			self.redraw_func()
	elif event.keyval == gtk.keysyms.F8:
		self.card_font_size -= 3
		if self.redraw_func:
			self.redraw_func()
		


    def set_html_doc(self, html_str):
        self.document.clear()
        self.document.open_stream('text/html')
        self.document.write_stream("""
<html><head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<meta name="viewport" content="user-scalable=yes, width=device-width,
    maximum-scale=0.6667" />
<style>
.q
{ font-family: "Deja-Vu Sans", sans-serif; font-size: %dpx; color:#0000ff;}
.a
{ font-family: "Deja-Vu Sans", sans-serif; font-size: %dpx; }
body { margin-top: 0px; padding: 0px; }
</style>
</head><body>
%s
</body></html>
""" % (self.card_font_size, self.card_font_size, html_str.replace('font-weight:600','font-weight:bold')))
        self.document.close_stream()
        self.view.set_document(self.document)

    def print_html_doc(self, html_str):
        self.set_html_doc(html_str)
        while (gtk.events_pending()):
            gtk.main_iteration()

    
    def set_question(self):
      # get new card
        self.opbuttonsbox.show()
        c = self.deck.getCard(orm=False)
        if not c:
          # try once more after refreshing queue
            self.deck._countsDirty = True
            self.deck.checkDue()
            c = self.deck.getCard(orm=False)
            if not c:
                self.answerbuttonbox.hide()
                self.resultbuttonbox.hide()
                self.learnmorebox.show()
                self.set_html_doc(self.deck.deckFinishedMsg())
        else:
            self.currentCard = c
            self.answerbuttonbox.show()
            #self.answerbutton.grab_focus()
            self.resultbuttonbox.hide()
            self.learnmorebox.hide()
            self.set_html_doc('<br/><br/><center><div class="q"> %s </div></center>' % 
                              self.prepareMedia(c.question).encode("utf-8"))

        if self.deck.modifiedSinceSave():
            self.savebuttonlabel.set_markup('<span color="red">save</span>')
        else:
            self.savebuttonlabel.set_markup('save')

        if self.currentCard and "marked" in self.currentCard.tags.lower():
            self.markbuttonlabel.set_markup('<span color="red">mark</span>')
        else:
            self.markbuttonlabel.set_markup('mark')
	self.redraw_func = self.set_question

    def set_q_a(self):
        if not self.currentCard:
            self.currentCard = deck.getCard(orm=False)
        c = self.currentCard

        self.opbuttonsbox.show()
        self.answerbuttonbox.hide()
        self.resultbuttonbox.show()
        self.learnmorebox.hide()
        #self.resbuttons[2].grab_focus()
        self.set_html_doc('<br/><br/><center><div class="q">%s</div> <br/><br/><div class="a"> %s </div></center>' % 
                          (self.prepareMedia(c.question, auto=False).encode("utf-8"), self.prepareMedia(c.answer).encode("utf-8")))
        for i in range(2, 5):
            self.resbuttons[i-1].set_label(self.deck.nextIntervalStr(c, i, True))
	self.redraw_func = self.set_q_a

    def answer(self, q):
        if self.currentCard:
            self.deck.answerCard(self.currentCard, int(q))

    def prepareMedia(self, string, auto=True):
        for (fullMatch, filename, replacementString) in mediaRefs(string):
            if fullMatch.startswith("["):
                try:
                    if (filename.lower().endswith(".mp3") or filename.lower().endswith(".wav")) and auto:
                        subprocess.Popen(["mplayer",
                                          os.path.join(self.deck.mediaDir(), filename)])
                except:
                    pass
                string = re.sub(re.escape(fullMatch), "", string)
            else:
                pass
                #string = re.sub(re.escape(fullMatch), '''
                #<img src="%(f)s">''' % {'f': relativeMediaPath(filename)}, string)
                #return string
        return string

    def err_dlg(self, msg):
        dialog = gtk.MessageDialog(None,0, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        dialog.run()
        dialog.destroy()
  
    def do_sync(self):
        if self.SYNC_USERNAME == "" or self.SYNC_PASSWORD == "" and \
            self.yesno_dlg(gtk.MESSAGE_QUESTION, "Do you want to set sync account?"):
            self.run_settings(None, None)
                    
        self.deck_save()
        page = "<br/><br/>"
        self.deck.lastLoaded = time.time()
        #syncing
        while 1:
            proxy = HttpSyncServerProxy(self.SYNC_USERNAME, self.SYNC_PASSWORD)
            try:
                proxy.connect("ankimini")
            except:
                self.err_dlg("Cant connect - check connection and username/password")
                return

            if not proxy.hasDeck(self.deck.syncName):
                self.err_dlg("Cant sync, no deck on server")
                return

            if abs(proxy.timestamp - time.time()) > 60:
                self.err_dlg("Your clock is off by more than 60 seconds. Syncing will not work until you fix this.")
                return

            client = SyncClient(self.deck)
            client.setServer(proxy)
                # need to do anything?
            proxy.deckName = self.deck.syncName
            if not client.prepareSync():
                return
                # summary
            page+="""
<html><head>
<meta name="viewport" content="user-scalable=yes, width=device-width,
    maximum-scale=0.6667" />
</head><body>\n
Fetching summary from server..<br>
"""
            self.print_html_doc(page)
            sums = client.summaries()
                # diff
            page+="Determining differences.."
            self.print_html_doc(page)
            payload = client.genPayload(sums)
                # send payload
            pr = client.payloadChangeReport(payload)
            page+="<br>" + pr + "<br>"
            page+="Sending payload...<br>"
            self.print_html_doc(page)
            res = client.server.applyPayload(payload)
                # apply reply
            page+="Applying reply..<br>"
            self.print_html_doc(page)
            client.applyPayloadReply(res)
                # finished. save deck, preserving mod time
            page+="Sync complete."
            self.print_html_doc(page)
            self.deck.rebuildQueue()
            self.deck.lastLoaded = self.deck.modified
            self.deck.s.flush()
            self.deck.s.commit()
        
    def deck_save(self):
        self.print_html_doc("<center><br/><br/>saving %s...</center>" % self.DECK_PATH)
        self.deck.save()        

    def replace_deck_with_file(self, fname):
        if self.deck:
            self.deck.close()
        self.deck = None
        self.update_recent_menu(self.DECK_PATH)

        self.DECK_PATH = fname
        if self.init_deck():
            self.set_question()
            self.set_stats()
            self.conf_client.set_string("/apps/anki/general/deck_path", self.DECK_PATH)
        else:
            self.DECK_PATH = ""

    def recentclick(self, widget, cmd):
        if self.deck and self.deck.modifiedSinceSave() and self.yesno_dlg(gtk.MESSAGE_QUESTION, "Save the current deck first?"):
            self.deck_save()

        self.replace_deck_with_file(cmd)

#        self.err_dlg("Open recent: %s" % cmd)


    def opbutclick(self, widget, cmd):
        if cmd == 'save':
            if self.deck:
                self.deck_save()
                self.set_question()
                self.set_stats()
        elif cmd == 'answer':
            self.set_q_a()
            self.set_stats()
        elif cmd == 'close':
            self.redraw_func = None
            if not self.deck:
                return

            if self.deck.modifiedSinceSave() and \
                    self.yesno_dlg(gtk.MESSAGE_QUESTION, "Save the current deck first?"):
                self.deck_save()
            self.deck.close()
            self.deck = None
            self.update_recent_menu(self.DECK_PATH)
            self.DECK_PATH = ""
            self.conf_client.set_string("/apps/anki/general/deck_path", self.DECK_PATH)
            self.opbuttonsbox.hide()
            self.answerbuttonbox.hide()
            self.resultbuttonbox.hide()
            self.set_html_doc('<center><div class="a"><br/><br/><br/>%s %s</div></center>' % 
                              (appname, appversion))
            self.statslabel.set_markup("T: 0/0 (0.0%) A: <b>0.0%</b>. ETA: <b>Unknown</b>")
            self.missinglabel.set_markup('<span foreground="red">0</span>+0+<span foreground="blue">0</span>')

        elif cmd == 'replay':
            self.prepareMedia(self.currentCard.question)
            self.prepareMedia(self.currentCard.answer)
        elif cmd == 'sync':
            if not self.deck:
                return

            self.opbuttonsbox.hide()
            self.answerbuttonbox.hide()
            self.resultbuttonbox.hide()
            self.do_sync()
            self.set_question()
            self.set_stats()
        elif cmd == 'mark':
            if "marked" in self.currentCard.tags.lower():
                t = parseTags(self.currentCard.tags)
                t.remove("Marked")
                self.currentCard.tags = joinTags(t)
            else:
                self.currentCard.tags = joinTags(parseTags(self.currentCard.tags) + ["Marked"])
            self.currentCard.toDB(self.deck.s)
            if self.currentCard and "marked" in self.currentCard.tags.lower():
                self.markbuttonlabel.set_markup('<span color="red">mark</span>')
            else:
                self.markbuttonlabel.set_markup('mark')
        elif cmd == 'learnmore':
            self.deck.extraNewCards += 5

            self.deck.refresh()
            self.deck.updateAllPriorities()
            self.deck.rebuildCounts()
            self.deck.rebuildQueue()
            self.set_question()
            self.set_stats()

        elif cmd == 'reviewearly':
            self.deck.reviewEarly = True
            self.deck.refresh()
            self.deck.updateAllPriorities()
            self.deck.rebuildCounts()
            self.deck.rebuildQueue()
            self.set_question()
            self.set_stats()



    def resclick(self, widget, number):
        self.answer(number)
        self.set_question()
        self.set_stats()

    def quit_save(self, *args):
        if self.deck and self.deck.modifiedSinceSave():
            dialog = gtk.MessageDialog(None,0, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, 
                                    "Save the current deck first?")
            rep = dialog.run()
            if rep == gtk.RESPONSE_YES:
                self.deck_save()

        if self.deck:
            self.deck.close()
        self.deck = None

        gtk.main_quit()

    # Commit changes to the GConf database. 
    def config_entry_commit (self, entry, *args):
        client = entry.get_data ('client')
        text = entry.get_chars (0, -1)

        key = entry.get_data ('key')

    # Unset if the string is zero-length, otherwise set
        if text:
            client.set_string (key, text)
        else:
            client.unset (key)

    # From gconf-basic-app
    # Create an entry used to edit the given config key 
    def create_config_entry (self, prefs_dialog, client, label, config_key, focus=False):
        hbox = gtk.HBox (False, 5)
        label = gtk.Label (label)
        entry = gtk.Entry ()

        hbox.pack_start (label, False, False, 0)
        hbox.pack_end (entry, False, False, 0)

        # this will print an error via default error handler
        # if the key isn't set to a string

        s = client.get_string (config_key)
        if s:
            entry.set_text (s)
  
        entry.set_data ('client', client)
        entry.set_data ('key', config_key)

        # Commit changes if the user focuses out, or hits enter; we don't
        # do this on "changed" since it'd probably be a bit too slow to
        # round-trip to the server on every "changed" signal.

        entry.connect ('focus_out_event', self.config_entry_commit)
        entry.connect ('activate', self.config_entry_commit)    

        # Set the entry insensitive if the key it edits isn't writable.
        # Technically, we should update this sensitivity if the key gets
        # a change notify, but that's probably overkill.

        entry.set_sensitive (client.key_is_writable (config_key))

        if focus:
            entry.grab_focus ()

        return hbox

    def run_settings(self, widget, event):
        dialog = gtk.Dialog ("Anki sync account",
                             None,
                             0,
                             (gtk.STOCK_CLOSE, gtk.RESPONSE_ACCEPT))

    # destroy dialog on button press
        dialog.connect ('response', lambda wid,ev: wid.destroy ())

        dialog.set_default_response (gtk.RESPONSE_ACCEPT)

        vbox = gtk.VBox (False, 5)
        vbox.set_border_width (5)

        dialog.vbox.pack_start (vbox)

        entry = self.create_config_entry (dialog, self.conf_client, "Username:", "/apps/anki/general/sync_username", True)
        vbox.pack_start (entry, False, False)

        entry = self.create_config_entry (dialog, self.conf_client, "Password:", "/apps/anki/general/sync_password")
        vbox.pack_start (entry, False, False)

        dialog.show_all()
        dialog.run()

        self.SYNC_USERNAME = self.conf_client.get_string("/apps/anki/general/sync_username")
        self.SYNC_PASSWORD = self.conf_client.get_string("/apps/anki/general/sync_password")

app = AnkiMiniApp()
app.run()
