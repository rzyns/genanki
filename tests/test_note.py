import itertools
import tempfile
import textwrap
import time
from typing import Any, NotRequired
import warnings
from unittest import mock

import anki.collection
import anki.decks
import anki.models
import pytest

import genanki
from genanki import builtin_models
from genanki import model
from genanki.util import guid_for


DECK_ID = anki.decks.DeckId(1702181380)


class MyModelSpec(model.ModelSpec[Any]):
    @model.spec
    class fields(model.FieldSpec):
        Question: str = model.field()
        Answer: str = model.field()

    @model.spec
    class templates(model.TemplateSpec[fields], fields=fields):
        card1: str = model.template({
            "qfmt": "{{Question}}",
            "afmt": '{{FrontSide}}<hr id="answer">{{Answer}}',
        })

my_model = genanki.Model(
    # model_id=anki.models.NotetypeId(1376484377),
    name="Simple Model",
    model_spec=MyModelSpec,
)


class NoteSubclassWithGuid[T: model.FieldSpec](genanki.Note[T]):
    @property
    def guid(self) -> str:
        return guid_for(self)


def test_ok():
    my_note = NoteSubclassWithGuid(
        model=my_model,
        fields=MyModelSpec.fields(Question="Capital of Argentina", Answer="Buenos Aires"),
    )

    # https://stackoverflow.com/a/45671804
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        my_note.write_to_db(
            mock.MagicMock(),
            mock.MagicMock(),
            mock.MagicMock(),
            itertools.count(int(time.time() * 1000)),
        )


class TestTags:
    def test_assign(self):
        n = NoteSubclassWithGuid(
            model=builtin_models.BASIC_MODEL,
            tags=["foo", "bar", "baz"],
            fields=MyModelSpec.fields(Question="foo", Answer="bar"),
        )

        with pytest.raises(ValueError):
            n.tags = ["foo", "bar", " baz"]

    def test_assign_element(self):
        n = NoteSubclassWithGuid(
            model=builtin_models.BASIC_MODEL,
            fields=MyModelSpec.fields(Question="foo", Answer="bar"),
            tags=["foo", "bar", "baz"],
        )

        n.tags[0] = "dankey_kang"
        with pytest.raises(ValueError):
            n.tags[0] = "dankey kang"

    def test_assign_slice(self):
        n = NoteSubclassWithGuid(
            model=builtin_models.BASIC_MODEL,
            fields=MyModelSpec.fields(Question="foo", Answer="bar"),
            tags=["foo", "bar", "baz"],
        )

        n.tags[1:3] = ["bowser", "daisy"]
        with pytest.raises(ValueError):
            n.tags[1:3] = ["bowser", "princess peach"]

    def test_append(self):
        n = NoteSubclassWithGuid(
            model=builtin_models.BASIC_MODEL,
            fields=MyModelSpec.fields(Question="foo", Answer="bar"),
            tags=["foo", "bar", "baz"],
        )

        n.tags.append("sheik_hashtag_melee")
        with pytest.raises(ValueError):
            n.tags.append("king dedede")

    def test_extend(self):
        n = NoteSubclassWithGuid(
            model=builtin_models.BASIC_MODEL,
            fields=MyModelSpec.fields(Question="foo", Answer="bar"),
            tags=["foo", "bar", "baz"],
        )

        n.tags.extend(["palu", "wolf"])
        with pytest.raises(ValueError):
            n.tags.extend(["dat fox doe"])

    def test_insert(self):
        n = NoteSubclassWithGuid(
            model=builtin_models.BASIC_MODEL,
            fields=MyModelSpec.fields(Question="foo", Answer="bar"),
            tags=["foo", "bar", "baz"],
        )

        n.tags.insert(0, "lucina")
        with pytest.raises(ValueError):
            n.tags.insert(0, "nerf joker pls")


class QuestionAnswerExtraModelSpec(model.ModelSpec[Any]):
    @model.spec
    class fields(model.FieldSpec):
        Question: str = model.field()
        Answer: str = model.field()
        Extra: NotRequired[str] = model.field(default="")

    @model.spec
    class templates(model.TemplateSpec[fields], fields=fields):
        card1: str = model.template({
            "qfmt": "{{Question}}",
            "afmt": '{{FrontSide}}<hr id="answer">{{Answer}}',
        })


def test_num_fields_equals_model_ok():
    m = genanki.Model(
        # model_id=1894808898,
        name="Test Model",
        model_spec=QuestionAnswerExtraModelSpec,
    )

    n = NoteSubclassWithGuid(
        model=m,
        fields=QuestionAnswerExtraModelSpec.fields(
            Question="What is the capital of Taiwan?",
            Answer="Taipei",
            Extra="Taipei was originally inhabitied by the Ketagalan people prior to the arrival of Han settlers in 1709.",
        ),
    )

    n.write_to_db(
        mock.MagicMock(),
        mock.MagicMock(),
        mock.MagicMock(),
        itertools.count(int(time.time() * 1000)),
    )
    # test passes if code gets to here without raising


class TestFindInvalidHtmlTagsInField:
    def test_ok(self):
        assert genanki.Note._find_invalid_html_tags_in_field("<h1>") == []

    def test_ok_with_space(self):
        assert genanki.Note._find_invalid_html_tags_in_field(" <h1> ") == []

    def test_ok_multiple(self):
        assert genanki.Note._find_invalid_html_tags_in_field("<h1>test</h1>") == []

    def test_ok_br(self):
        assert genanki.Note._find_invalid_html_tags_in_field("<br>") == []

    def test_ok_br2(self):
        assert genanki.Note._find_invalid_html_tags_in_field("<br/>") == []

    def test_ok_br3(self):
        assert genanki.Note._find_invalid_html_tags_in_field("<br />") == []

    def test_ok_attrs(self):
        assert (
            genanki.Note._find_invalid_html_tags_in_field(
                '<h1 style="color: red">STOP</h1>'
            )
            == []
        )

    def test_ok_uppercase(self):
        assert genanki.Note._find_invalid_html_tags_in_field("<TD></Td>") == []

    def test_ng_empty(self):
        assert genanki.Note._find_invalid_html_tags_in_field(" hello <> goodbye") == [
            "<>"
        ]

    def test_ng_empty_space(self):
        assert genanki.Note._find_invalid_html_tags_in_field(" hello < > goodbye") == [
            "< >"
        ]

    def test_ng_invalid_characters(self):
        assert genanki.Note._find_invalid_html_tags_in_field("<@h1>") == ["<@h1>"]

    def test_ng_invalid_characters_end(self):
        assert genanki.Note._find_invalid_html_tags_in_field("<h1@>") == ["<h1@>"]

    def test_ng_issue_28(self):
        latex_code = r"""
        [latex]
        \schemestart
        \chemfig{*6(--(<OH)-(<:Br)---)}
        \arrow{->[?]}
        \chemfig{*6(--(<[:30]{O}?)(<:H)-?[,{>},](<:H)---)}
        \schemestop
        [/latex]
        """
        latex_code = textwrap.dedent(latex_code[1:])

        expected_invalid_tags = [
            "<OH)-(<:Br)---)}\n\\arrow{->",
            "<[:30]{O}?)(<:H)-?[,{>",
        ]

        assert (
            genanki.Note._find_invalid_html_tags_in_field(latex_code)
            == expected_invalid_tags
        )

    def test_ok_html_comment(self):
        # see https://github.com/kerrickstaley/genanki/issues/108
        assert (
            genanki.Note._find_invalid_html_tags_in_field("<!-- here is a comment -->")
            == []
        )

    def test_ok_cdata(self):
        # see https://github.com/kerrickstaley/genanki/issues/108
        assert (
            genanki.Note._find_invalid_html_tags_in_field(
                "<![CDATA[ here is some cdata ]]>"
            )
            == []
        )


class SimpleModelSpec(model.ModelSpec[Any]):
    @model.spec
    class fields(model.FieldSpec):
        Question: str = model.field()
        Answer: str = model.field()

    @model.spec
    class templates(model.TemplateSpec[fields], fields=fields):
        card1: str = model.template({
            "qfmt": "{{Question}}",
            "afmt": '{{FrontSide}}<hr id="answer">{{Answer}}',
        })


def test_warns_on_invalid_html_tags():
    my_model = genanki.Model(
        # model_id=1376484377,
        name="Simple Model",
        model_spec=SimpleModelSpec,
    )

    with pytest.raises(
        ValueError, match="^Field contained the following invalid HTML tags.*$"
    ):
        NoteSubclassWithGuid(
            model=my_model, fields=SimpleModelSpec.fields(Question="Capital of <$> Argentina", Answer="Buenos Aires")
        )



def test_suppress_warnings():
    my_model = genanki.Model(
        # model_id=1376484377,
        name="Simple Model",
        model_spec=SimpleModelSpec,
    )


    with pytest.raises(ValueError):
        warnings.simplefilter("error")
        warnings.filterwarnings(
            "ignore",
            message="^Field contained the following invalid HTML tags",
            module="genanki",
        )

        NoteSubclassWithGuid(
            model=my_model, fields=SimpleModelSpec.fields(Question="Capital of <$> Argentina", Answer="Buenos Aires")
        )


# https://github.com/kerrickstaley/genanki/issues/121
def test_does_not_warn_on_html_tags_in_guid():
    my_note = NoteSubclassWithGuid(
        model=genanki.BASIC_MODEL,
        fields=SimpleModelSpec.fields(Question="Capital of Iowa", Answer="Des Moines"),
        guid="Gt<p8{N2>Z",
    )

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        my_note.write_to_db(
            mock.MagicMock(),
            mock.MagicMock(),
            mock.MagicMock(),
            itertools.count(int(time.time() * 1000)),
        )


class FuriganaSpec(model.ModelSpec[Any]):
    @model.spec
    class fields(model.FieldSpec):
        Question: str = model.field()
        Answer: str = model.field()

    @model.spec
    class templates(model.TemplateSpec[fields], fields=fields):
        card1: str = model.template({
            "qfmt": "{{Question}}",
            "afmt": '{{FrontSide}}<hr id="answer">{{furigana:Answer}}',
        })


def test_furigana_field():
    # Fields like {{furigana:Reading}} are supported by the Japanese Support plugin:
    # https://ankiweb.net/shared/info/3918629684
    # Japanese Support is quasi-official (it was created by Damien Elmes, the creator of Anki) and so
    # we support it in genanki.
    my_model = genanki.Model(
        # model_id=1523004567,
        name="Japanese",
        model_spec=FuriganaSpec,
    )

    my_note = NoteSubclassWithGuid(model=my_model, fields=FuriganaSpec.fields(Question="kanji character", Answer="漢字[かんじ]"))

    my_deck = genanki.Deck(deck_id=DECK_ID, name="Japanese")
    my_deck.add_note(my_note)

    with tempfile.NamedTemporaryFile(delete=True, delete_on_close=False) as tempf:
        pkg = genanki.Package(my_deck)

        pkg.write_to_file(tempf.name)
        # test passes if there is no exception
