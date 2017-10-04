# Copyright 2016 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.


from random import randrange

import re
import wikipedia as wiki
from adapt.intent import IntentBuilder
from os.path import join, dirname

from mycroft.skills.core import FallbackSkill, intent_handler
from mycroft.util import read_stripped_lines


class EnglishQuestionParser(object):
    """
    Poor-man's english question parser. Not even close to conclusive, but
    appears to construct some decent w|a queries and responses.
    """

    def __init__(self):
        self.regexes = [
            re.compile(
                ".*(?P<QuestionWord>who|what|when|where|why|which|how) "
                "(?P<QuestionVerb>\w+) (?P<Query>.*)")
        ]

    def _normalize(self, groupdict):
        if 'Query' in groupdict:
            return groupdict
        elif 'Query1' and 'Query2' in groupdict:
            return {
                'QuestionWord': groupdit.get('QuestionWord'),
                'QuestionVerb': groupdict.get('QuestionVerb'),
                'Query': ' '.join([groupdict.get('Query1'), groupdict.get(
                    'Query2')])
            }

    def parse(self, utterance):
        for regex in self.regexes:
            match = regex.match(utterance)
            if match:
                return self._normalize(match.groupdict())
        return None


class WikipediaFallback(FallbackSkill):
    def __init__(self):
        super(WikipediaFallback, self).__init__()
        self.fallback_parser = EnglishQuestionParser()
        self.disabmiguate = None

    def initialize(self):
        self.register_fallback(self.handle_fallback, 8)
        self.register_fallback(self.handle_disambiguate, 100)

    def handle_fallback(self, message):
        utterance = message.data.get('utterance', '')
        parsed_question = self.fallback_parser.parse(utterance)
        if parsed_question:
            title = parsed_question.get('Query')
            results = wiki.search(title, 1)
            try:
                summary = re.sub(
                    r'\([^)]*\)|/[^/]*/', '',
                    wiki.summary(results[0], 1))
                self.disambiguate = None
            except wiki.DisambiguationError as e:
                # remove last two entries and limit to three items
                self.disambiguate = e.options[:-2]
                summary = None

            if summary:
                self.speak(summary)
                return True
        return False

    def handle_disambiguate(self, message):
        if self.disambiguate:
            if len(self.disambiguate) >= 3:
                data = {'alt1': self.disambiguate[0],
                        'alt2': self.disambiguate[1],
                        'alt3': self.disambiguate[2]}
                print data
                # More than three options
                self.speak_dialog('disambiguate.more.than.three',
                                  data=data,
                                  expect_response=True)
            elif len(self.disambiguate) == 3:
                    # Three alternatives
                    self.speak_dialog('disambiguate.three',
                                      data=data,
                                      expect_response=True)
            elif len(self.disabmiguate) == 2:
                data = {'alt1': self.disambiguate[0],
                        'alt2': self.disambiguate[1]}
                self.speak_dialog('disambiguate.two', data=data,
                                  expect_response=True)
            else:
                self.disambiguate = None
                return False
            self.disambiguate = None
            self.set_context('DisambiguationContext')
            return True
        return False

    @intent_handler(IntentBuilder('A').require('DisambiguationContext') \
                                   .require('DisambiguationTitle'))
    def handle_disambiguation_response(self, message):
        self.remove_context('DisambiguationContext')
        title = message.data.get('DisambiguationTitle')
        if title:
            try:
                results = wiki.search(title, 1)
                summary = re.sub(
                    r'\([^)]*\)|/[^/]*/', '',
                    wiki.summary(results[0], 1))
                self.disambiguate = None
                self.speak(summary)
            except:
                pass


    def stop(self):
        pass


def create_skill():
    return WikipediaFallback()
