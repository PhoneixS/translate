#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2002-2006,2008-2009 Zuza Software Foundation
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
import collections
import types

"""Convert Gettext PO localization files back to Windows Resource (.rc) files.

See: http://docs.translatehouse.org/projects/translate-toolkit/en/latest/commands/rc2po.html
for examples and usage instructions.
"""

from translate.convert import convert
from translate.storage import po, rc

NL = "\n"
BLOCK_START = "BEGIN"
BLOCK_END = "END"

def is_iterable_but_not_string(o):
    """Check if object is iterable but not a string."""
    return isinstance(o, collections.Iterable) and not isinstance(o, types.StringTypes)

class rerc:

    def __init__(self, templatefile, charset="utf-8", lang=None, sublang=None):
        self.templatefile = templatefile
        self.inputdict = {}
        self.charset = charset
        self.lang = lang
        self.sublang = sublang
        
    def convert_dialog(self, s, loc, toks):
        out = []
        out.append(toks.block_id)
        out.append(" ")
        out.append(toks.block_type)
        if toks.caption:
            out.append(" ")
            out.append(toks.pre_caption)
            out.append("CAPTION ") # The string caption
            
            name = rc.generate_dialog_caption_name(toks.block_type, toks.block_id[0])
            if name in self.inputdict:
                out.append('"' + self.inputdict[name] + '"')
            else:
                out.append(toks.caption)
            
            out.extend(toks.post_caption) # The rest of the options
            out.append(NL)
        else:
            out.append(" ")
            out.extend(toks.post_caption) # The rest of the options
            out.append(NL)
        
        out.append(BLOCK_START)
        out.append(NL)
        
        for c in toks.controls:
            
            out.append("    ")
            if len(c[0]) >= 16:
                out.append(c[0])
                # If more than 16 char, put it on a new line to align it.
                out.append("\n"+" "*(16+4))
            else:
                out.append(c[0].ljust(16))
            
            tmp = []
            
            name = rc.generate_dialog_control_name(toks.block_type, toks.block_id[0], c.id_control[0], c.values_[1])
            if name in self.inputdict:
                tmp.append('"')
                tmp.append(self.inputdict[name])
                tmp.append('"')
            elif is_iterable_but_not_string(c[1]):
                tmp.append(" | ".join(c[1]))
            else:
                tmp.append(c[1])
            
            for a in c[2:]:
                if is_iterable_but_not_string(a):
                    tmp.append(" | ".join(a))
                else:
                    tmp.append(a)
            
            out.append(u",".join(tmp))
            out.append(NL)
        
        out.append(BLOCK_END)
        
        return out

    def convert_string_table(self, s, loc, toks):
        out = []
        out.extend(toks[0:2])
        out.append(NL)
        out.append(BLOCK_START)
        out.append(NL)
        
        for c in toks.controls:
            out.append("    ")
            if len(c[0]) >= 24:
                out.append(c[0])
                out.append("\n"+" "*(24+4))
            else:
                out.append(c[0].ljust(24))
            
            name = rc.generate_stringtable_name(c[0])
            if name in self.inputdict:
                c[1] = '"' + self.inputdict[name] + '"'
            
            out.append(",".join(c[1:]))
            out.append(NL)
        
        out.append(BLOCK_END)
        
        return out

    def convert_language(self, s, loc, toks):
        out = []
        out.append("LANGUAGE ")
        out.append(self.lang)
        if self.sublang:
            out.append(", ")
            out.append(self.sublang)
        return out

    def convert_popup(self, popup, ident=1):
        out = []
        
        identation = " " * (4 * ident)
        
        out.append(identation)
        out.append(popup.block_type)
        if popup.caption:
            out.append(" ")
            out.append(popup.pre_caption)
            out.append(popup.caption)
            out.extend(popup.post_caption) # The rest of the options
            out.append(NL)
        else:
            out.append(" ")
            out.extend(popup.post_caption) # The rest of the options
            out.append(NL)
        
        out.append(identation)
        out.append(BLOCK_START)
        out.append(NL)
        
        for element in popup.elements:
            
            if element.block_type and element.block_type == "MENUITEM":
                out.append(identation)
                out.append("    MENUITEM")
                out.append(" ")
                
                if element.values_ and len(element.values_) >= 2:
                    out.append(", ".join(element.values_))
                elif element.values_[0] == "SEPARATOR":
                    out.append("SEPARATOR")
                else:
                    raise NotImplementedError()
                
                out.append(NL)
                
            elif element.popups:
                for sub_popup in element.popups:
                    out.extend(self.convert_popup(sub_popup, ident+1))
        out.append(identation)
        out.append(BLOCK_END)
        out.append(NL)
        
        return out

    def convert_menu(self, s, loc, toks):
        out = []
        
        out.append(toks.block_id)
        out.append(" ")
        out.append(toks.block_type)
        if toks.caption:
            out.append(" ")
            out.append(toks.pre_caption)
            out.append("CAPTION ") # The string caption
            out.append(toks.caption)
            out.extend(toks.post_caption) # The rest of the options
            out.append(NL)
        else:
            out.append(" ")
            out.extend(toks.post_caption) # The rest of the options
            out.append(NL)
        
        out.append(BLOCK_START)
        out.append(NL)
        
        
        for p in toks.popups:
            out.extend(self.convert_popup(p))
        
        out.append(BLOCK_END)
        
        return out

    def translate_strings(self, s, loc, toks):
        """ Change the strings in the toks by the ones in the translation. """
        
        if toks.language:
            # Recreate the language, but using the settings.
            return self.convert_language(s, loc, toks)
        
        if toks.block_type:
            if toks.block_type == "DIALOGEX" or toks.block_type == "DIALOG":
                return self.convert_dialog(s, loc, toks)
            
            if toks.block_type == "STRINGTABLE":
                return self.convert_string_table(s, loc, toks)
            
            if toks.block_type == "MENU":
                return self.convert_menu(s, loc, toks)
        
        return toks

    def convertstore(self, inputstore, includefuzzy=False):
        self.makestoredict(inputstore, includefuzzy)
        
        # TODO Parse the file replacing the strings.
        
        statement = rc.rc_statement()
        statement.addParseAction(self.translate_strings)
        return statement.transformString(self.templatefile.read().decode(self.charset))

    def makestoredict(self, store, includefuzzy=False):
        """ make a dictionary of the translations"""
        for unit in store.units:
            if includefuzzy or not unit.isfuzzy():
                for location in unit.getlocations():
                    rcstring = unit.target
                    if len(rcstring.strip()) == 0:
                        rcstring = unit.source
                    self.inputdict[location] = rc.escape_to_rc(rcstring)

    def convertblock(self, block):
        newblock = block
        if isinstance(newblock, unicode):
            newblock = newblock.encode('utf-8')
        if newblock.startswith("LANGUAGE"):
            return "LANGUAGE %s, %s" % (self.lang, self.sublang)
        for unit in self.templatestore.units:
            location = unit.getlocations()[0]
            if location in self.inputdict:
                if self.inputdict[location] != unit.match.groupdict()['value']:
                    newmatch = unit.match.group().replace(unit.match.groupdict()['value'],
                                                          self.inputdict[location])
                    newblock = newblock.replace(unit.match.group(), newmatch)
        if isinstance(newblock, unicode):
            newblock = newblock.encode(self.charset)
        return newblock


def convertrc(inputfile, outputfile, templatefile, includefuzzy=False,
              charset=None, lang=None, sublang=None, outputthreshold=None):
    inputstore = po.pofile(inputfile)

    if not convert.should_output_store(inputstore, outputthreshold):
        return False

    if not lang:
        raise ValueError("must specify a target language")
    if templatefile is None:
        raise ValueError("must have template file for rc files")
        # convertor = po2rc()
    else:
        convertor = rerc(templatefile, charset, lang, sublang)
    outputrclines = convertor.convertstore(inputstore, includefuzzy)
    outputfile.write(outputrclines.encode('ISO-8859-15'))
    return 1


def main(argv=None):
    # handle command line options
    formats = {("po", "rc"): ("rc", convertrc)}
    parser = convert.ConvertOptionParser(formats, usetemplates=True,
                                         description=__doc__)
    defaultcharset = "utf-8"
    parser.add_option("", "--charset", dest="charset", default=defaultcharset,
        help="charset to use to decode the RC files (default: %s)" % defaultcharset,
        metavar="CHARSET")
    parser.add_option("-l", "--lang", dest="lang", default=None,
        help="LANG entry", metavar="LANG")
    defaultsublang = "SUBLANG_DEFAULT"
    parser.add_option("", "--sublang", dest="sublang", default=defaultsublang,
        help="SUBLANG entry (default: %s)" % defaultsublang, metavar="SUBLANG")
    parser.passthrough.append("charset")
    parser.passthrough.append("lang")
    parser.passthrough.append("sublang")
    parser.add_threshold_option()
    parser.add_fuzzy_option()
    parser.run(argv)

if __name__ == '__main__':
    main()
