#!/usr/bin/env python2.5
import gtkhtml2
import gtk
import hildon

import time, cgi, sys, os, re, subprocess
from anki import DeckStorage as ds
from anki.sync import SyncClient, HttpSyncServerProxy
from anki.media import mediaRefs
from anki.utils import parseTags, joinTags

def request_object(*args):
    print 'request object', args

global DECK_PATH, SYNC_USERNAME, SYNC_PASSWORD
configFile = os.path.expanduser("~/.ankimini-config.py")
try:
    execfile(configFile)
except:
    dialog = gtk.MessageDialog(None,0, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, \
                               "Can't read the config file %s. Did you install it?\n"%configFile)
    dialog.run()
    dialog.destroy()
    raise

class AnkiMiniApp(hildon.Program):

    currentCard = None
    deck = None
    played = False

    DECK_PATH = DECK_PATH
    SYNC_USERNAME = SYNC_USERNAME
    SYNC_PASSWORD = SYNC_PASSWORD

    def __init__(self):
        hildon.Program.__init__(self)

        self.window = hildon.Window()
        self.window.connect("destroy", gtk.main_quit)
        self.window.connect("delete_event", gtk.main_quit)
        self.window.connect("key-press-event", self.on_key_press)
        self.window.connect("window-state-event", self.on_window_state_change)
        self.window_in_fullscreen = False 
        
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

        self.document.clear()
        self.document.open_stream('text/html')
        self.document.write_stream('<html><head></head><body>question <b> is </b> this <br></body></html>')
        self.document.close_stream()
        self.view = gtkhtml2.View()
        self.view.set_document(self.document)
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
        menu_item = gtk.MenuItem("Choose Deck...")
        menu_item.connect("activate", self.choose_deck, "choose_deck")
        menu_item.show()

        menuItemSave = gtk.MenuItem("Save")
        menuItemSave.connect("activate", self.opbutclick, "save")
        menuItemSeparator = gtk.SeparatorMenuItem()

        menuItemExit = gtk.MenuItem("Exit")
        menuItemExit.connect("activate", gtk.main_quit, "quit")

        self.menu.append(menu_item)
        self.menu.append(menuItemSave)
        self.menu.append(menuItemExit)
        self.window.set_menu(self.menu)

    def init_deck(self):
        print "open deck.. " + self.DECK_PATH
        if not os.path.exists(self.DECK_PATH):
            self.err_dlg("Couldn't open your deck. Please check config.")
            return

        self.deck = ds.Deck(self.DECK_PATH, backup=False)
        self.deck.rebuildQueue()

    def choose_deck(self, widget, event):
        selector=hildon.FileChooserDialog(self.window,gtk.FILE_CHOOSER_ACTION_OPEN)
        rep=selector.run()
        selector.hide()
        a=selector.get_filename()
        if rep==gtk.RESPONSE_OK:
            self.DECK_PATH = a
            self.init_deck()
            self.set_question()
            self.set_stats()
        selector.destroy()

    def run(self):
        self.window.show_all()
        configFile = os.path.expanduser("~/.ankimini-config.py")
        try:
            execfile(configFile)
        except:
            self.err_dlg("Can't read the config file (%s). Did you install it?" % configFile)
            raise

        self.init_deck()
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

    def set_html_doc(self, html_str):
        self.document.clear()
        self.document.open_stream('text/html')
        self.document.write_stream("""
<html><head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<style>
.q
{ font-size: 30px; color:#0000ff;}
.a
{ font-size: 30px; }
body { margin-top: 0px; padding: 0px; }
</style>
</head><body>
%s
</body></html>
""" % html_str)
        self.document.close_stream()
        self.view.set_document(self.document)
    
    def set_question(self):
      # get new card
        c = self.deck.getCard(orm=False)
        if not c:
          # try once more after refreshing queue
            self.deck._countsDirty = True
            self.deck.checkDue()
            c = self.deck.getCard(orm=False)
            if not c:
                self.answerbuttonbox.hide()
                self.resultbuttonbox.hide()
                self.set_html_doc(self.deck.deckFinishedMsg())
        else:
            self.currentCard = c
            self.answerbuttonbox.show()
            self.resultbuttonbox.hide()
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

    def set_q_a(self):
        if not self.currentCard:
            self.currentCard = deck.getCard(orm=False)
        c = self.currentCard

        self.answerbuttonbox.hide()
        self.resultbuttonbox.show()
        self.set_html_doc('<br/><br/><center><div class="q">%s</div> <br/><br/><div class="a"> %s </div></center>' % 
                          (self.prepareMedia(c.question, auto=False).encode("utf-8"), self.prepareMedia(c.answer).encode("utf-8")))
        for i in range(2, 5):
            self.resbuttons[i-1].set_label(self.deck.nextIntervalStr(c, i, True))

    def answer(self, q):
        if self.currentCard:
            self.deck.answerCard(self.currentCard, int(q))

    def prepareMedia(self, string, auto=True):
        for (fullMatch, filename, replacementString) in mediaRefs(string):
            if fullMatch.startswith("["):
                if filename.lower().endswith(".mp3") and auto:
                    subprocess.Popen(["mplayer",
                                      os.path.join(self.deck.mediaDir(), filename)])
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
        page = "<br/><br/>"
        self.deck.save()
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
            self.set_html_doc(page)
            while (gtk.events_pending()):
                gtk.main_iteration()
            sums = client.summaries()
                # diff
            page+="Determining differences..<br>"
            self.set_html_doc(page)
            while (gtk.events_pending()):
                gtk.main_iteration()
            payload = client.genPayload(sums)
                # send payload
            pr = client.payloadChangeReport(payload)
            page+="<br>" + pr + "<br>"
            page+="Sending payload...<br>"
            self.set_html_doc(page)
            while (gtk.events_pending()):
                gtk.main_iteration()
            res = client.server.applyPayload(payload)
                # apply reply
            page+="Applying reply..<br>"
            self.set_html_doc(page)
            while (gtk.events_pending()):
                gtk.main_iteration()
            client.applyPayloadReply(res)
                # finished. save deck, preserving mod time
            page+="Sync complete."
            self.set_html_doc(page)
            while (gtk.events_pending()):
                gtk.main_iteration()
            self.deck.rebuildQueue()
            self.deck.lastLoaded = self.deck.modified
            self.deck.s.flush()
            self.deck.s.commit()
        
                              
    def opbutclick(self, widget, cmd):
        if cmd == 'save':
            self.set_html_doc("<center><br/><br/>saving %s...</center>" % DECK_PATH)
            while (gtk.events_pending()):
                gtk.main_iteration()
            self.deck.save()
            self.set_question()
            self.set_stats()
        elif cmd == 'answer':
            self.set_q_a()
            self.set_stats()
        elif cmd == 'replay':
            self.prepareMedia(self.currentCard.question)
            self.prepareMedia(self.currentCard.answer)
        elif cmd == 'sync':
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

                              
    def resclick(self, widget, number):
        self.answer(number)
        self.set_question()
        self.set_stats()

app = AnkiMiniApp()
app.run()
