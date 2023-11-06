#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# kanji_colorizer.py is part of kanji-colorize which makes KanjiVG data
# into colored stroke order diagrams; this is the anki2 addon file.
#
# Copyright 2012 Cayenne Boyer
#
# The code to do this automatically when the Kanji field is exited was
# originally based on the Japanese support reading generation addon by
# Damien Elmes
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/>.

# Installation: copy this file and the kanjicolorizer directory to your
# Anki addons folder.

# Usage: Add a "Diagram" field to a model with "Japanese"
# in the name and a field named "Kanji".  When you finish editing the
# kanji field, if it contains precisely one character, a colored stroke
# order diagram will be added to the Diagram field in the same way that
# the Japanese support plugin adds readings.
#
# To add diagrams to all such fields, or regenerate them with new
# settings, use the "Kanji Colorizer: (re)generate all" option in the
# tools menu.


from anki.hooks import addHook
from aqt import mw
from aqt.utils import showInfo, askUser
from aqt.qt import *
from .kanjicolorizer.colorizer import (KanjiVG, KanjiColorizer,
                                       InvalidCharacterError)


def make_kanji_colorizer(data):
    config = "--mode "
    config += data["mode"]
    if data["group-mode"]:
        config += " --group-mode "
    config += " --saturation "
    config += str(data["saturation"])
    config += " --value "
    config += str(data["value"])
    config += " --image-size "
    config += str(data["image-size"])

    return KanjiColorizer(config)


class Profile:
    def __init__(self, data):
        self.kanji_colorizer = make_kanji_colorizer(data)

        self.model_name_substr = data['model'].lower() if 'model' in data and type(
            data['model']) is str else 'japanese'
        self.src_field = data['src-field'] if 'src-field' in data and type(
            data['src-field']) is str else 'Kanji'
        self.dst_field = data['dst-field'] if 'dst-field' in data and type(
            data['dst-field']) is str else 'Diagram'
        self.overwrite_dest = data['overwrite-dest'] if 'overwrite-dest' in data and type(
            data['overwrite-dest']) is bool else True

        self.diagrammed_characters = data['diagrammed-characters']\


    def model_is_correct_type(self, model):
        '''
        Returns True if model has Japanese in the name and has both srcField
        and dstField; otherwise returns False
        '''
        # Does the model name have Japanese in it?
        model_name = model['name'].lower()
        fields = mw.col.models.fieldNames(model)
        return (self.model_name_substr in model_name and
                self.src_field in fields and
                self.dst_field in fields)

    def characters_to_colorize(self, s):
        '''
        Given a string, returns a list of characters to colorize

        If the string mixes kanji and other characters, it will return
        only the kanji. Otherwise it will return all characters.
        '''
        if self.diagrammed_characters == 'all':
            return list(s)
        elif self.diagrammed_characters == 'kanji':
            return [c for c in s if is_kanji(c)]
        else:
            just_kanji = [c for c in s if is_kanji(c)]
            if len(just_kanji) >= 1:
                return just_kanji
            return list(s)

    def addKanji(self, note, flag=False, current_field_index=None):
        '''
        Checks to see if a kanji should be added, and adds it if so.
        '''
        if current_field_index != None:  # We've left a field
            # But it isn't the relevant one
            if note.model()['flds'][current_field_index]['name'] != self.src_field:
                return flag

        srcTxt = mw.col.media.strip(note[self.src_field])

        oldDst = note[self.dst_field]
        dst = ''

        for character in self.characters_to_colorize(str(srcTxt)):
            # write to file; anki works in the media directory by default
            try:
                filename = KanjiVG(character).ascii_filename
            except InvalidCharacterError:
                # silently ignore non-Japanese characters
                continue
            char_svg = self.kanji_colorizer.get_colored_svg(
                character).encode('utf_8')
            anki_fname = mw.col.media.writeData(filename, char_svg)
            dst += '<img src="{!s}">'.format(anki_fname)

        if oldDst != '' and not self.overwrite_dest:
            return flag

        if dst != oldDst and dst != '':
            note[self.dst_field] = dst
            # if we're editing an existing card, flush the changes
            if note.id != 0:
                note.flush()
            return True

        return flag


# Configuration
addon_config = mw.addonManager.getConfig(__name__)

profiles_json = addon_config['profiles'] if addon_config['profiles'] else []

profiles = [Profile(p) for p in profiles_json]


def is_kanji(c):
    '''
    Boolean indicating if the character is in the kanji unicode range
    '''
    return ord(c) >= 19968 and ord(c) <= 40879


# Add a colorized kanji to a Diagram whenever leaving a Kanji field

def onFocusLost(flag, note, currentFieldIndex):
    for p in profiles:
        if p.model_is_correct_type(note.model()):
            return p.addKanji(note, flag, currentFieldIndex)

    return flag


addHook('editFocusLost', onFocusLost)


# menu item to regenerate all

def regenerate_all():
    # Find the models that have the right name and fields; faster than
    # checking every note
    if not askUser("Do you want to regenerate all kanji diagrams? "
                   'This may take some time and will overwrite the '
                   'destination Diagram fields.'):
        return

    for p in profiles:
        models = [m for m in mw.col.models.all() if p.model_is_correct_type(m)]
        # Find the notes in those models and give them kanji
        for model in models:
            for nid in mw.col.models.nids(model):
                p.addKanji(mw.col.getNote(nid))

    showInfo("Done regenerating colorized kanji diagrams!")


def generate_for_new():
    if not askUser("This option will generate diagrams for notes with "
                   "an empty destination field only. "
                   "Proceed?"):
        return
    for p in profiles:
        model_ids = [mid for mid in mw.col.models.ids(
        ) if p.model_is_correct_type(mw.col.models.get(mid))]
        if not model_ids:
            showInfo(
                "Can not find any relevant models. Make sure model, src-field,-and dst-field are set correctly in your config.")
            return
        # Generate search string in the format
        #    (mid:123 or mid:456) Kanji:_* Diagram:
        search_str = '({}) {}:_* {}:'.format(
            ' or '.join(('mid:'+str(mid) for mid in model_ids)), p.src_field, p.dst_field)
        # Find the notes
        for note_id in mw.col.findNotes(search_str):
            p.addKanji(mw.col.getNote(note_id))
    showInfo("Done generating colorized kanji diagrams!")


# add menu items
submenu = mw.form.menuTools.addMenu("Kanji Colorizer")

do_generate_new = QAction("generate all new", mw)
do_generate_new.triggered.connect(generate_for_new)
submenu.addAction(do_generate_new)

do_regenerate_all = QAction("(re)generate all", mw)
do_regenerate_all.triggered.connect(regenerate_all)
submenu.addAction(do_regenerate_all)
