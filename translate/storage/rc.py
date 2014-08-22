#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2004-2006,2008-2009 Zuza Software Foundation
#
# This file is part of the Translate Toolkit.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

"""Classes that hold units of .rc files (:class:`rcunit`) or entire files
(:class:`rcfile`) used in translating Windows Resources.

.. note:::

   This implementation is based mostly on observing WINE .rc files,
   these should mimic other non-WINE .rc files.
"""

import re

from translate.storage import base

from pyparsing import restOfLine, cStyleComment, Word, alphanums, alphas,\
    Optional, SkipTo, ZeroOrMore, Group, Keyword, quotedString, delimitedList,\
    nums, commaSeparatedList, Forward


def escape_to_python(string):
    """Escape a given .rc string into a valid Python string."""
    pystring = re.sub('"\s*\\\\\n\s*"', "", string)   # xxx"\n"xxx line continuation
    pystring = re.sub("\\\\\\\n", "", pystring)       # backslash newline line continuation
    pystring = re.sub("\\\\n", "\n", pystring)        # Convert escaped newline to a real newline
    pystring = re.sub("\\\\t", "\t", pystring)        # Convert escape tab to a real tab
    pystring = re.sub("\\\\\\\\", "\\\\", pystring)   # Convert escape backslash to a real escaped backslash
    return pystring


def escape_to_rc(string):
    """Escape a given Python string into a valid .rc string."""
    rcstring = re.sub("\\\\", "\\\\\\\\", string)
    rcstring = re.sub("\t", "\\\\t", rcstring)
    rcstring = re.sub("\n", "\\\\n", rcstring)
    return rcstring


class rcunit(base.TranslationUnit):
    """A unit of an rc file"""

    def __init__(self, source="", encoding="cp1252"):
        """Construct a blank rcunit."""
        super(rcunit, self).__init__(source)
        self.name = ""
        self._value = ""
        self.comments = []
        self.source = source
        self.match = None
        self.encoding = encoding

    def setsource(self, source):
        """Sets the source AND the target to be equal"""
        self._rich_source = None
        self._value = source or ""

    def getsource(self):
        return self._value

    source = property(getsource, setsource)

    def settarget(self, target):
        """.. note:: This also sets the ``.source`` attribute!"""
        self._rich_target = None
        self.source = target

    def gettarget(self):
        return self.source
    target = property(gettarget, settarget)

    def __str__(self):
        """Convert to a string. Double check that unicode is handled somehow here."""
        source = self.getoutput()
        if isinstance(source, unicode):
            return source.encode(getattr(self, "encoding", "UTF-8"))
        return source

    def getoutput(self):
        """Convert the element back into formatted lines for a .rc file."""
        if self.isblank():
            return "".join(self.comments + ["\n"])
        else:
            return "".join(self.comments + ["%s=%s\n" % (self.name, self.value)])

    def getlocations(self):
        return [self.name]

    def addnote(self, text, origin=None, position="append"):
        self.comments.append(text)

    def getnotes(self, origin=None):
        return '\n'.join(self.comments)

    def removenotes(self):
        self.comments = []

    def isblank(self):
        """Returns whether this is a blank element, containing only comments."""
        return not (self.name or self.value)


class rcfile(base.TranslationStore):
    """This class represents a .rc file, made up of rcunits."""
    UnitClass = rcunit

    def __init__(self, inputfile=None, lang=None, sublang=None, encoding="cp1252"):
        """Construct an rcfile, optionally reading in from inputfile."""
        self.encoding = encoding
        super(rcfile, self).__init__(unitclass=self.UnitClass)
        self.filename = getattr(inputfile, 'name', '')
        self.lang = lang
        self.sublang = sublang
        if inputfile is not None:
            rcsrc = inputfile.read().decode(encoding)
            inputfile.close()
            self.parse(rcsrc)

    def rc_statement(self):
        """ Generate a RC statement parser that can be used to parse a RC file

        :rtype: pyparsing.ParserElement
        """

        one_line_comment = '//' + restOfLine

        comments = cStyleComment ^ one_line_comment

        precompiler = Word('#', alphanums) + restOfLine

        language_definition = "LANGUAGE" + Word(alphas + '_').setResultsName(
            "language") + Optional(',' + Word(alphas + '_').setResultsName("sublanguage"))

        block_start = (Keyword('{') | Keyword("BEGIN")).setName("block_start")
        block_end = (Keyword('}') | Keyword("END")).setName("block_end")

        reserved_words = block_start | block_end

        name_id = ~reserved_words + \
            Word(alphas, alphanums + '_').setName("name_id")

        constant = Optional(Keyword("NOT")) + name_id

        combined_constants = delimitedList(constant, '|')

        numbers = Word(nums)

        block_options = Optional(SkipTo(
            Keyword("CAPTION"), include=True, failOn=block_start) + quotedString("caption")) + SkipTo(block_start)

        undefined_control = Group(name_id.setResultsName(
            "id_control") + delimitedList(quotedString ^ constant ^ numbers ^ combined_constants).setResultsName("values_"))

        block = block_start + \
            ZeroOrMore(undefined_control)("controls") + block_end

        dialog = name_id(
            "block_id") + (Keyword("DIALOGEX") | Keyword("DIALOG"))("block_type") + block_options + block

        string_table = Keyword("STRINGTABLE")(
            "block_type") + block_options + block

        menu_item = Keyword(
            "MENUITEM")("type") + (commaSeparatedList("values_") | Keyword("SEPARATOR"))

        popup_block = Forward()

        popup_block <<= Group(Keyword("POPUP")("type") + Optional(quotedString("caption")) + block_start +
                              ZeroOrMore(Group(menu_item | popup_block))("elements") + block_end)("popups*")

        menu = name_id("block_id") + \
            Keyword("MENU")("block_type") + block_options + \
            block_start + ZeroOrMore(popup_block) + block_end

        statem = comments ^ precompiler ^ language_definition ^ dialog ^ string_table ^ menu

        return statem

    def add_popup_units(self, pre_name, popup):
        """Transverses the popup tree making new units as needed."""

        if popup.caption:
            newunit = rcunit(escape_to_python(popup.caption[1:-1]))
            newunit.name = "%s.POPUP.CAPTION" % (pre_name)
            newunit.match = popup
            self.addunit(newunit)

        for element in popup.elements:

            if element.type and element.type == "MENUITEM":

                if element.values_ and len(element.values_) >= 2:
                    newunit = rcunit(escape_to_python(element.values_[0][1:-1]))
                    newunit.name = "%s.%s.%s" % (
                        pre_name, element.type, element.values_[1])
                    newunit.match = element
                    self.addunit(newunit)
                # Else it can be a separator.
            elif element.popups:
                for sub_popup in element.popups:
                    self.add_popup_units(
                        "%s.%s" % (pre_name, popup.caption[1:-1].replace(" ", "_")), sub_popup)

    def parse(self, rcsrc):
        """Read the source of a .rc file in and include them as units."""

        # Parse the strings into a structure.
        results = self.rc_statement().searchString(rcsrc)

        processblocks = False

        for statement in results:

            if statement.language:

                if self.lang is None or statement.language == self.lang:
                    if self.sublang is None or statement.sublanguage == self.sublang:
                        processblocks = True
                    else:
                        processblocks = False
                else:
                    processblocks = False
                continue

            if processblocks and statement.block_type:

                if statement.block_type in ("DIALOG", "DIALOGEX"):

                    if statement.caption:
                        newunit = rcunit(escape_to_python(statement.caption[1:-1]))
                        newunit.name = "%s.%s.%s" % (
                            statement.block_type, statement.block_id[0], "CAPTION")
                        newunit.match = statement
                        self.addunit(newunit)

                    for control in statement.controls:

                        if control.id_control[0] in ("AUTOCHECKBOX AUTORADIOBUTTON CAPTION CHECKBOX CTEXT CONTROL DEFPUSHBUTTON GROUPBOX LTEXT PUSHBUTTON RADIOBUTTON RTEXT")\
                                and (control.values_[0].startswith('"') or control.values_[0].startswith("'")):

                            # The first value without quoted chars.
                            newunit = rcunit(
                                escape_to_python(control.values_[0][1:-1]))
                            newunit.name = "%s.%s.%s.%s" % (
                                statement.block_type, statement.block_id[0], control.id_control[0], control.values_[1])
                            newunit.match = control
                            self.addunit(newunit)

                    continue

                if statement.block_type in ("MENU"):

                    pre_name = "%s.%s" % (
                        statement.block_type, statement.block_id[0])

                    for popup in statement.popups:

                        self.add_popup_units(pre_name, popup)

                    continue

                if statement.block_type in ("STRINGTABLE"):

                    for text in statement.controls:

                        newunit = rcunit(escape_to_python(text.values_[0][1:-1]))
                        newunit.name = "STRINGTABLE." + text.id_control[0]
                        newunit.match = text
                        self.addunit(newunit)

                    continue

    def __str__(self):
        """Convert the units back to lines."""
        return "".join(self.blocks)
