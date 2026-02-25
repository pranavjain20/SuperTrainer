"""Tests for the Claude transcript parser — tool schema validation,
response extraction, and API interaction (mocked)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.parser import (
    DEFAULT_MODEL,
    EXERCISE_CARD_TOOL,
    MODIFY_EXERCISE_CARD_TOOL,
    OBSERVATION_CARD_TOOL,
    PARSER_SYSTEM_PROMPT,
    PARSER_TOOLS,
    _build_exercise_card,
    _build_observation_card,
    _extract_parser_result,
    format_session_context,
    parse_transcript,
)


# ===================================================================
# Mock helpers
# ===================================================================


def _make_tool_use_block(
    name: str,
    tool_input: dict,
    block_id: str = "toolu_test123",
) -> MagicMock:
    """Build a mock content block that looks like Claude's tool_use response.

    Claude returns content blocks with .type, .name, and .input attributes.
    This builds a MagicMock that mimics that structure.
    """
    block = MagicMock()
    block.type = "tool_use"
    block.id = block_id
    block.name = name
    block.input = tool_input
    return block


def _make_text_block(text: str = "Let me parse that for you.") -> MagicMock:
    """Build a mock text content block (these should be ignored by the parser)."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _make_mock_response(content_blocks: list[MagicMock]) -> MagicMock:
    """Build a mock Claude messages.create() response."""
    response = MagicMock()
    response.content = content_blocks
    return response


def _patch_anthropic(content_blocks: list[MagicMock]):
    """Create a patch decorator that mocks the Anthropic client.

    Returns the patch object. The mocked client's messages.create()
    will return a response containing the given content blocks.
    """
    mock_response = _make_mock_response(content_blocks)
    mock_client = AsyncMock()
    mock_client.messages.create.return_value = mock_response

    return patch(
        "app.services.parser.anthropic.AsyncAnthropic",
        return_value=mock_client,
    )


# ===================================================================
# Input validation
# ===================================================================


@pytest.mark.asyncio(loop_scope="session")
class TestParseTranscriptValidation:
    """Tests for input validation before the API call."""

    async def test_rejects_empty_string(self):
        with pytest.raises(ValueError, match="must not be empty"):
            await parse_transcript("")

    async def test_rejects_whitespace_only(self):
        with pytest.raises(ValueError, match="must not be empty"):
            await parse_transcript("   \n\t  ")


# ===================================================================
# Exercise card parsing
# ===================================================================


@pytest.mark.asyncio(loop_scope="session")
class TestParseTranscriptExerciseCards:
    """Tests for parsing exercise cards from Claude's tool_use responses."""

    async def test_single_exercise_with_sets(self):
        """Basic case: one exercise with reps and weight."""
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "bench press",
                "sets": [
                    {"reps": 10, "weight": 80, "weight_unit": "kg"},
                    {"reps": 10, "weight": 80, "weight_unit": "kg"},
                    {"reps": 10, "weight": 80, "weight_unit": "kg"},
                ],
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("bench press 3 sets of 10 at 80 kilos")

        assert len(result.exercise_cards) == 1
        card = result.exercise_cards[0]
        assert card.exercise_name == "bench press"
        assert len(card.sets) == 3
        assert all(s.reps == 10 for s in card.sets)
        assert all(s.weight == 80 for s in card.sets)
        assert all(s.weight_unit == "kg" for s in card.sets)

    async def test_exercise_with_form_notes(self):
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "squat",
                "sets": [{"reps": 8}],
                "form_notes": ["good depth", "knees tracking well"],
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("squat 8 reps good depth knees tracking well")

        card = result.exercise_cards[0]
        assert card.form_notes == ("good depth", "knees tracking well")

    async def test_exercise_with_cues(self):
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "deadlift",
                "sets": [{"reps": 5, "weight": 100, "weight_unit": "kg"}],
                "cues_given": ["drive through your heels", "chest up"],
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("deadlift 5 at 100 kilos cued drive through heels chest up")

        card = result.exercise_cards[0]
        assert card.cues_given == ("drive through your heels", "chest up")

    async def test_exercise_with_rpe(self):
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "bench press",
                "sets": [{"reps": 8, "weight": 85, "weight_unit": "kg", "rpe": 8.5}],
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("bench 8 reps at 85 kilos RPE 8.5")

        s = result.exercise_cards[0].sets[0]
        assert s.rpe == 8.5

    async def test_exercise_with_duration(self):
        """Timed exercises like planks use duration_seconds instead of weight."""
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "plank",
                "sets": [{"reps": 1, "duration_seconds": 60}],
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("plank hold for 60 seconds")

        s = result.exercise_cards[0].sets[0]
        assert s.duration_seconds == 60
        assert s.weight is None

    async def test_exercise_with_pounds(self):
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "bench press",
                "sets": [{"reps": 10, "weight": 185, "weight_unit": "lbs"}],
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("bench press 10 reps at 185 pounds")

        s = result.exercise_cards[0].sets[0]
        assert s.weight == 185
        assert s.weight_unit == "lbs"

    async def test_exercise_no_sets(self):
        """Trainer just names the exercise without any set details."""
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "Romanian deadlift",
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("next up Romanian deadlift")

        card = result.exercise_cards[0]
        assert card.exercise_name == "Romanian deadlift"
        assert card.sets is None
        assert card.form_notes == ()
        assert card.cues_given == ()

    async def test_multiple_exercises(self):
        """One transcript can produce multiple exercise cards."""
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "bench press",
                "sets": [{"reps": 10, "weight": 80, "weight_unit": "kg"}],
            }, block_id="toolu_1"),
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "incline dumbbell press",
                "sets": [{"reps": 12, "weight": 30, "weight_unit": "kg"}],
            }, block_id="toolu_2"),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript(
                "bench press 10 at 80 kilos then incline dumbbell press 12 at 30 kilos"
            )

        assert len(result.exercise_cards) == 2
        assert result.exercise_cards[0].exercise_name == "bench press"
        assert result.exercise_cards[1].exercise_name == "incline dumbbell press"

    async def test_exercise_weight_without_unit(self):
        """Weight mentioned but no unit — weight_unit should be None."""
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "squat",
                "sets": [{"reps": 5, "weight": 100}],
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("squat 5 reps at 100")

        s = result.exercise_cards[0].sets[0]
        assert s.weight == 100
        assert s.weight_unit is None

    async def test_exercise_mixed_set_fields(self):
        """Realistic case: weight + rpe but no weight_unit."""
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "squat",
                "sets": [{"reps": 5, "weight": 100, "rpe": 9}],
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("squat 5 at 100 RPE 9")

        s = result.exercise_cards[0].sets[0]
        assert s.reps == 5
        assert s.weight == 100
        assert s.weight_unit is None
        assert s.rpe == 9

    async def test_malformed_set_missing_reps_skipped(self):
        """If Claude somehow returns a set without reps, it should be skipped."""
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "bench press",
                "sets": [
                    {"reps": 10, "weight": 80},
                    {"weight": 80},  # malformed — no reps
                    {"reps": 10, "weight": 80},
                ],
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("bench press sets at 80")

        card = result.exercise_cards[0]
        assert len(card.sets) == 2  # malformed set was skipped
        assert all(s.reps == 10 for s in card.sets)

    async def test_all_sets_malformed_becomes_none(self):
        """If every set is malformed (no reps), sets should be None, not empty tuple."""
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "bench press",
                "sets": [
                    {"weight": 80},
                    {"weight": 85},
                ],
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("bench press some sets")

        card = result.exercise_cards[0]
        assert card.sets is None  # all malformed → treated as no sets


# ===================================================================
# Observation card parsing
# ===================================================================


@pytest.mark.asyncio(loop_scope="session")
class TestParseTranscriptObservationCards:
    """Tests for parsing observation cards from Claude's tool_use responses."""

    async def test_general_observation(self):
        blocks = [
            _make_tool_use_block("record_observation_card", {
                "observation_text": "Client arrived 10 minutes late, seemed rushed.",
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("Marcus showed up 10 minutes late seemed rushed")

        assert len(result.observation_cards) == 1
        card = result.observation_cards[0]
        assert card.observation_text == "Client arrived 10 minutes late, seemed rushed."
        assert card.flag_color is None
        assert card.flag_reason is None

    async def test_red_flag_pain(self):
        blocks = [
            _make_tool_use_block("record_observation_card", {
                "observation_text": "Client reported sharp pain in right knee during last set.",
                "flag_color": "red",
                "flag_reason": "client reported sharp knee pain",
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("he said sharp pain in his right knee on the last set")

        card = result.observation_cards[0]
        assert card.flag_color == "red"
        assert card.flag_reason == "client reported sharp knee pain"

    async def test_yellow_flag_fatigue(self):
        blocks = [
            _make_tool_use_block("record_observation_card", {
                "observation_text": "Client showing signs of fatigue, lower energy than usual.",
                "flag_color": "yellow",
                "flag_reason": "unusual fatigue and low energy",
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("Marcus seems really fatigued today lower energy than usual")

        card = result.observation_cards[0]
        assert card.flag_color == "yellow"

    async def test_green_flag_positive(self):
        blocks = [
            _make_tool_use_block("record_observation_card", {
                "observation_text": "New personal record on squat — 120kg for 5 reps.",
                "flag_color": "green",
                "flag_reason": "new personal record",
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("PR on squat 120 kilos for 5 reps")

        card = result.observation_cards[0]
        assert card.flag_color == "green"
        assert card.flag_reason == "new personal record"

    async def test_neutral_observation_no_flag(self):
        """Neutral observations should have no flag_color or flag_reason."""
        blocks = [
            _make_tool_use_block("record_observation_card", {
                "observation_text": "Client mentioned they've been sleeping better this week.",
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("he said he's been sleeping better this week")

        card = result.observation_cards[0]
        assert card.flag_color is None
        assert card.flag_reason is None

    async def test_flag_color_without_reason(self):
        """Schema can't enforce 'required if flag_color set' — Claude may omit reason.

        JSON Schema doesn't support conditional required fields. The description
        tells Claude to include flag_reason when flag_color is set, but nothing
        guarantees it. This test documents the behavior: flag_color present,
        flag_reason None. The validation layer (Day 4) should catch this.
        """
        blocks = [
            _make_tool_use_block("record_observation_card", {
                "observation_text": "Client seemed uncomfortable during overhead work.",
                "flag_color": "yellow",
                # flag_reason intentionally omitted
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("seemed uncomfortable during overhead stuff")

        card = result.observation_cards[0]
        assert card.flag_color == "yellow"
        assert card.flag_reason is None  # known gap, validation layer handles


# ===================================================================
# Mixed responses (exercise + observation)
# ===================================================================


@pytest.mark.asyncio(loop_scope="session")
class TestParseTranscriptMixed:
    """Tests for transcripts that produce both exercise and observation cards."""

    async def test_exercise_plus_observation(self):
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "squat",
                "sets": [{"reps": 5, "weight": 100, "weight_unit": "kg"}],
            }, block_id="toolu_1"),
            _make_tool_use_block("record_observation_card", {
                "observation_text": "Client mentioned mild lower back tightness.",
                "flag_color": "yellow",
                "flag_reason": "lower back tightness reported",
            }, block_id="toolu_2"),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript(
                "squat 5 at 100 kilos also he mentioned his lower back feels a bit tight"
            )

        assert len(result.exercise_cards) == 1
        assert len(result.observation_cards) == 1
        assert result.exercise_cards[0].exercise_name == "squat"
        assert result.observation_cards[0].flag_color == "yellow"

    async def test_text_blocks_ignored(self):
        """Claude sometimes returns text blocks alongside tool calls. We ignore them."""
        blocks = [
            _make_text_block("I'll parse this transcript for you."),
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "bench press",
                "sets": [{"reps": 10}],
            }),
            _make_text_block("Done parsing."),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("bench press 10 reps")

        assert len(result.exercise_cards) == 1
        assert len(result.observation_cards) == 0

    async def test_unknown_tool_name_silently_skipped(self):
        """If Claude calls an unrecognized tool, it should be skipped (not crash)."""
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "bench press",
                "sets": [{"reps": 10}],
            }, block_id="toolu_1"),
            _make_tool_use_block("some_unknown_tool", {
                "data": "unexpected",
            }, block_id="toolu_2"),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("bench press 10 reps and something weird")

        assert len(result.exercise_cards) == 1
        assert len(result.observation_cards) == 0
        # Unknown tool still captured in raw_tool_calls for debugging
        assert len(result.raw_tool_calls) == 2
        assert result.raw_tool_calls[1]["name"] == "some_unknown_tool"

    async def test_empty_tool_input_skipped(self):
        """Empty input dict {} → malformed block skipped, doesn't crash."""
        blocks = [
            _make_tool_use_block("record_exercise_card", {}, block_id="toolu_1"),
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "squat",
                "sets": [{"reps": 5}],
            }, block_id="toolu_2"),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("something garbled then squat 5 reps")

        # Malformed block skipped, valid block parsed
        assert len(result.exercise_cards) == 1
        assert result.exercise_cards[0].exercise_name == "squat"
        # Both still captured in raw_tool_calls for debugging
        assert len(result.raw_tool_calls) == 2
        assert result.raw_tool_calls[0]["input"] == {}

    async def test_empty_observation_input_skipped(self):
        """Empty observation_card input {} → skipped gracefully."""
        blocks = [
            _make_tool_use_block("record_observation_card", {}),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("some garbled speech")

        assert len(result.observation_cards) == 0
        assert len(result.raw_tool_calls) == 1


# ===================================================================
# Debug / raw tool calls
# ===================================================================


@pytest.mark.asyncio(loop_scope="session")
class TestParseTranscriptDebug:
    """Tests for the raw_tool_calls debug field."""

    async def test_raw_tool_calls_captured(self):
        """raw_tool_calls should contain the original tool name and input for debugging."""
        tool_input = {
            "exercise_name": "bench press",
            "sets": [{"reps": 10, "weight": 80, "weight_unit": "kg"}],
        }
        blocks = [_make_tool_use_block("record_exercise_card", tool_input)]
        with _patch_anthropic(blocks):
            result = await parse_transcript("bench press 10 at 80 kilos")

        assert len(result.raw_tool_calls) == 1
        assert result.raw_tool_calls[0]["name"] == "record_exercise_card"
        assert result.raw_tool_calls[0]["input"] == tool_input


# ===================================================================
# API interaction (verify correct arguments passed to Claude)
# ===================================================================


@pytest.mark.asyncio(loop_scope="session")
class TestParseTranscriptAPIInteraction:
    """Tests that verify the correct arguments are passed to the Claude API."""

    async def _get_create_call_kwargs(self, transcript: str, **kwargs) -> dict:
        """Helper: call parse_transcript and return the kwargs passed to messages.create()."""
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "bench press",
                "sets": [{"reps": 10}],
            }),
        ]
        mock_response = _make_mock_response(blocks)
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        with patch(
            "app.services.parser.anthropic.AsyncAnthropic",
            return_value=mock_client,
        ):
            await parse_transcript(transcript, **kwargs)

        return mock_client.messages.create.call_args.kwargs

    async def test_uses_default_model(self):
        kwargs = await self._get_create_call_kwargs("bench press 10 reps")
        assert kwargs["model"] == DEFAULT_MODEL

    async def test_custom_model(self):
        kwargs = await self._get_create_call_kwargs(
            "bench press 10 reps",
            model="claude-haiku-4-5-20251001",
        )
        assert kwargs["model"] == "claude-haiku-4-5-20251001"

    async def test_passes_tool_choice_any(self):
        kwargs = await self._get_create_call_kwargs("bench press 10 reps")
        assert kwargs["tool_choice"] == {"type": "any"}

    async def test_passes_all_parser_tools(self):
        kwargs = await self._get_create_call_kwargs("bench press 10 reps")
        assert kwargs["tools"] == PARSER_TOOLS

    async def test_passes_system_prompt(self):
        kwargs = await self._get_create_call_kwargs("bench press 10 reps")
        assert kwargs["system"] == PARSER_SYSTEM_PROMPT

    async def test_passes_transcript_as_user_message(self):
        transcript = "bench press 3 sets of 10 at 80 kilos good form"
        kwargs = await self._get_create_call_kwargs(transcript)
        assert kwargs["messages"] == [{"role": "user", "content": transcript}]

    async def test_passes_context_plus_transcript_as_user_message(self):
        """When session_context is provided, user message includes both."""
        context = [
            {
                "entry_type": "exercise_card",
                "exercise_name": "bench press",
                "sets": [{"reps": 10, "weight": 80, "weight_unit": "kg"}],
            },
        ]
        kwargs = await self._get_create_call_kwargs(
            "RPE 8 on those",
            session_context=context,
        )
        user_msg = kwargs["messages"][0]["content"]
        assert "Session context" in user_msg
        assert "bench press" in user_msg
        assert "RPE 8 on those" in user_msg

    async def test_no_context_sends_raw_transcript(self):
        """Without session_context, user message is just the transcript (backward compat)."""
        transcript = "squat 5 reps at 100 kilos"
        kwargs = await self._get_create_call_kwargs(transcript, session_context=None)
        assert kwargs["messages"] == [{"role": "user", "content": transcript}]


# ===================================================================
# Session context formatting
# ===================================================================


class TestFormatSessionContext:
    """Tests for format_session_context() — turning prior entries into
    readable text Claude can reference by numbered IDs."""

    def test_empty_entries_returns_empty_string(self):
        assert format_session_context([]) == ""

    def test_single_exercise_card(self):
        entries = [
            {
                "entry_type": "exercise_card",
                "exercise_name": "bench press",
                "sets": [
                    {"reps": 10, "weight": 80, "weight_unit": "kg"},
                    {"reps": 10, "weight": 80, "weight_unit": "kg"},
                    {"reps": 10, "weight": 80, "weight_unit": "kg"},
                ],
            },
        ]
        result = format_session_context(entries)
        assert "Session context (1 entries logged so far):" in result
        assert "[1] Exercise: bench press" in result
        assert "3x10 reps @ 80kg" in result

    def test_exercise_card_with_varying_sets(self):
        entries = [
            {
                "entry_type": "exercise_card",
                "exercise_name": "squat",
                "sets": [
                    {"reps": 8, "weight": 100, "weight_unit": "kg"},
                    {"reps": 5, "weight": 120, "weight_unit": "kg"},
                ],
            },
        ]
        result = format_session_context(entries)
        assert "Set 1: 8 reps @ 100kg" in result
        assert "Set 2: 5 reps @ 120kg" in result

    def test_exercise_card_with_form_notes_and_cues(self):
        entries = [
            {
                "entry_type": "exercise_card",
                "exercise_name": "deadlift",
                "sets": [{"reps": 5, "weight": 140, "weight_unit": "kg"}],
                "form_notes": ["good lockout", "slight back rounding"],
                "cues_given": ["chest up", "drive through heels"],
            },
        ]
        result = format_session_context(entries)
        assert "Form: good lockout, slight back rounding" in result
        assert "Cues: chest up, drive through heels" in result

    def test_exercise_card_no_sets(self):
        """Exercise named but no set details — should still format cleanly."""
        entries = [
            {
                "entry_type": "exercise_card",
                "exercise_name": "Romanian deadlift",
            },
        ]
        result = format_session_context(entries)
        assert "[1] Exercise: Romanian deadlift" in result
        assert "Sets:" not in result

    def test_observation_card_neutral(self):
        entries = [
            {
                "entry_type": "observation_card",
                "observation_text": "Client arrived 10 minutes late.",
            },
        ]
        result = format_session_context(entries)
        assert "[1] Observation: Client arrived 10 minutes late." in result
        assert "flag" not in result

    def test_observation_card_with_flag(self):
        entries = [
            {
                "entry_type": "observation_card",
                "observation_text": "Sharp pain in right knee.",
                "flag_color": "red",
                "flag_reason": "client reported sharp knee pain",
            },
        ]
        result = format_session_context(entries)
        assert "[1] Observation: Sharp pain in right knee." in result
        assert "(red flag: client reported sharp knee pain)" in result

    def test_observation_card_flag_without_reason(self):
        entries = [
            {
                "entry_type": "observation_card",
                "observation_text": "Seemed tired.",
                "flag_color": "yellow",
            },
        ]
        result = format_session_context(entries)
        assert "(yellow flag)" in result

    def test_multiple_mixed_entries(self):
        """Multiple entries of different types, numbered sequentially."""
        entries = [
            {
                "entry_type": "exercise_card",
                "exercise_name": "bench press",
                "sets": [{"reps": 10, "weight": 80, "weight_unit": "kg"}],
            },
            {
                "entry_type": "observation_card",
                "observation_text": "Good energy today.",
            },
            {
                "entry_type": "exercise_card",
                "exercise_name": "squat",
                "sets": [{"reps": 5, "weight": 100, "weight_unit": "kg"}],
            },
        ]
        result = format_session_context(entries)
        assert "Session context (3 entries logged so far):" in result
        assert "[1] Exercise: bench press" in result
        assert "[2] Observation: Good energy today." in result
        assert "[3] Exercise: squat" in result

    def test_set_with_rpe(self):
        entries = [
            {
                "entry_type": "exercise_card",
                "exercise_name": "bench press",
                "sets": [{"reps": 8, "weight": 85, "weight_unit": "kg", "rpe": 8.5}],
            },
        ]
        result = format_session_context(entries)
        assert "RPE 8.5" in result

    def test_set_with_duration(self):
        entries = [
            {
                "entry_type": "exercise_card",
                "exercise_name": "plank",
                "sets": [{"reps": 1, "duration_seconds": 60}],
            },
        ]
        result = format_session_context(entries)
        assert "(60s)" in result

    def test_set_weight_without_unit(self):
        """Weight present but no unit — should show just the number."""
        entries = [
            {
                "entry_type": "exercise_card",
                "exercise_name": "squat",
                "sets": [{"reps": 5, "weight": 100}],
            },
        ]
        result = format_session_context(entries)
        assert "@ 100" in result
        # Should NOT have "kg" or "lbs" appended
        assert "100kg" not in result
        assert "100lbs" not in result

    def test_unknown_entry_type(self):
        entries = [{"entry_type": "something_weird"}]
        result = format_session_context(entries)
        assert "[1] Unknown entry type: something_weird" in result

    def test_set_summary_includes_rir(self):
        entries = [
            {
                "entry_type": "exercise_card",
                "exercise_name": "squat",
                "sets": [{"reps": 5, "weight": 100, "weight_unit": "kg", "rir": 2}],
            },
        ]
        result = format_session_context(entries)
        assert "RIR 2" in result

    def test_set_summary_includes_equipment_note(self):
        entries = [
            {
                "entry_type": "exercise_card",
                "exercise_name": "squat",
                "sets": [
                    {"reps": 10, "weight": 60, "weight_unit": "kg", "equipment_note": "with a red band"},
                ],
            },
        ]
        result = format_session_context(entries)
        assert "[with a red band]" in result


# ===================================================================
# Modify tool schema validation
# ===================================================================


# ===================================================================
# RIR + equipment_note schema & extraction
# ===================================================================


class TestRirEquipmentNoteSchema:
    """Tests that rir and equipment_note fields exist in the tool schemas."""

    def test_exercise_card_tool_has_rir(self):
        set_props = EXERCISE_CARD_TOOL["input_schema"]["properties"]["sets"]["items"]["properties"]
        assert "rir" in set_props
        assert set_props["rir"]["type"] == "number"

    def test_exercise_card_tool_has_equipment_note(self):
        set_props = EXERCISE_CARD_TOOL["input_schema"]["properties"]["sets"]["items"]["properties"]
        assert "equipment_note" in set_props
        assert set_props["equipment_note"]["type"] == "string"

    def test_modify_tool_has_rir(self):
        update_props = MODIFY_EXERCISE_CARD_TOOL["input_schema"]["properties"]["updates"]["properties"]
        assert "rir" in update_props
        assert update_props["rir"]["type"] == "number"

    def test_modify_tool_has_equipment_note(self):
        update_props = MODIFY_EXERCISE_CARD_TOOL["input_schema"]["properties"]["updates"]["properties"]
        assert "equipment_note" in update_props
        assert update_props["equipment_note"]["type"] == "string"


@pytest.mark.asyncio(loop_scope="session")
class TestRirEquipmentNoteExtraction:
    """Tests that rir and equipment_note are correctly extracted from tool calls."""

    async def test_rir_only(self):
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "squat",
                "sets": [{"reps": 5, "weight": 100, "weight_unit": "kg", "rir": 2}],
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("squat 5 at 100 RIR 2")

        assert len(result.exercise_cards) == 1
        assert result.exercise_cards[0].sets[0].rir == 2
        assert result.exercise_cards[0].sets[0].equipment_note is None

    async def test_equipment_note_only(self):
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "squat",
                "sets": [{"reps": 6, "weight": 60, "weight_unit": "kg", "equipment_note": "with a red band"}],
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("squat 6 at 60 with a red band")

        assert len(result.exercise_cards) == 1
        assert result.exercise_cards[0].sets[0].equipment_note == "with a red band"
        assert result.exercise_cards[0].sets[0].rir is None

    async def test_rir_and_equipment_note_together(self):
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "squat",
                "sets": [
                    {"reps": 10, "weight": 60, "weight_unit": "kg", "rir": 3, "equipment_note": "with a band"},
                    {"reps": 10, "weight": 60, "weight_unit": "kg", "rir": 3, "equipment_note": "with a band"},
                    {"reps": 10, "weight": 60, "weight_unit": "kg", "rir": 3, "equipment_note": "with a band"},
                ],
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("squats with a band 3x10 at 60 RIR 3")

        card = result.exercise_cards[0]
        assert len(card.sets) == 3
        for s in card.sets:
            assert s.rir == 3
            assert s.equipment_note == "with a band"


class TestModifyExerciseCardToolSchema:
    """Tests for the modify_exercise_card tool schema structure."""

    def test_tool_name(self):
        assert MODIFY_EXERCISE_CARD_TOOL["name"] == "modify_exercise_card"

    def test_required_fields(self):
        required = MODIFY_EXERCISE_CARD_TOOL["input_schema"]["required"]
        assert "target_entry_id" in required
        assert "action" in required

    def test_action_enum_values(self):
        action_prop = MODIFY_EXERCISE_CARD_TOOL["input_schema"]["properties"]["action"]
        assert action_prop["enum"] == ["add", "correct"]

    def test_tool_in_parser_tools_list(self):
        tool_names = [t["name"] for t in PARSER_TOOLS]
        assert "modify_exercise_card" in tool_names


# ===================================================================
# Modification parsing
# ===================================================================


@pytest.mark.asyncio(loop_scope="session")
class TestParseTranscriptModifications:
    """Tests for parsing modify_exercise_card tool calls."""

    async def test_add_rpe_to_all_sets(self):
        """Trainer says 'RPE 8 on those' — adds RPE to all sets of entry [1]."""
        blocks = [
            _make_tool_use_block("modify_exercise_card", {
                "target_entry_id": 1,
                "action": "add",
                "updates": {"rpe": 8},
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("RPE 8 on those")

        assert len(result.modifications) == 1
        mod = result.modifications[0]
        assert mod.target_entry_id == 1
        assert mod.action == "add"
        assert mod.target_sets is None  # all sets
        assert mod.updates == {"rpe": 8}

    async def test_add_rpe_to_specific_sets(self):
        """Trainer says 'RPE 8 on sets 2 through 4'."""
        blocks = [
            _make_tool_use_block("modify_exercise_card", {
                "target_entry_id": 1,
                "action": "add",
                "target_sets": [2, 3, 4],
                "updates": {"rpe": 8},
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("RPE 8 on sets 2 through 4")

        mod = result.modifications[0]
        assert mod.target_sets == (2, 3, 4)
        assert mod.updates == {"rpe": 8}

    async def test_correct_weight(self):
        """Trainer says 'no wait, 85 not 80' — corrects weight on entry [1]."""
        blocks = [
            _make_tool_use_block("modify_exercise_card", {
                "target_entry_id": 1,
                "action": "correct",
                "updates": {"weight": 85},
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("no wait it was 85 not 80")

        mod = result.modifications[0]
        assert mod.action == "correct"
        assert mod.updates == {"weight": 85}

    async def test_add_form_notes(self):
        """Trainer adds form notes to an existing exercise."""
        blocks = [
            _make_tool_use_block("modify_exercise_card", {
                "target_entry_id": 2,
                "action": "add",
                "form_notes": ["knees caving in on last set"],
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("also knees were caving in on those squats")

        mod = result.modifications[0]
        assert mod.target_entry_id == 2
        assert mod.form_notes == ("knees caving in on last set",)
        assert mod.updates is None

    async def test_add_cues(self):
        """Trainer adds coaching cues to an existing exercise."""
        blocks = [
            _make_tool_use_block("modify_exercise_card", {
                "target_entry_id": 1,
                "action": "add",
                "cues_given": ["drive through heels", "brace your core"],
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("I told him drive through heels and brace core on the bench")

        mod = result.modifications[0]
        assert mod.cues_given == ("drive through heels", "brace your core")

    async def test_correct_single_set(self):
        """Correcting weight on only set 3."""
        blocks = [
            _make_tool_use_block("modify_exercise_card", {
                "target_entry_id": 1,
                "action": "correct",
                "target_sets": [3],
                "updates": {"weight": 90, "weight_unit": "kg"},
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("actually set 3 was at 90 kilos")

        mod = result.modifications[0]
        assert mod.target_sets == (3,)
        assert mod.updates == {"weight": 90, "weight_unit": "kg"}

    async def test_modification_with_no_updates_or_notes(self):
        """Edge case: modify call with only required fields."""
        blocks = [
            _make_tool_use_block("modify_exercise_card", {
                "target_entry_id": 1,
                "action": "add",
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("something about entry 1")

        mod = result.modifications[0]
        assert mod.updates is None
        assert mod.form_notes == ()
        assert mod.cues_given == ()

    async def test_new_exercise_plus_modification_in_same_clip(self):
        """Trainer records a new exercise AND modifies an existing one."""
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "incline press",
                "sets": [{"reps": 12, "weight": 30, "weight_unit": "kg"}],
            }, block_id="toolu_1"),
            _make_tool_use_block("modify_exercise_card", {
                "target_entry_id": 1,
                "action": "add",
                "updates": {"rpe": 7},
            }, block_id="toolu_2"),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript(
                "incline press 12 at 30 kilos also RPE 7 on the bench from earlier"
            )

        assert len(result.exercise_cards) == 1
        assert result.exercise_cards[0].exercise_name == "incline press"
        assert len(result.modifications) == 1
        assert result.modifications[0].target_entry_id == 1

    async def test_modification_captured_in_raw_tool_calls(self):
        """Modify tool calls should appear in raw_tool_calls for debugging."""
        tool_input = {
            "target_entry_id": 1,
            "action": "add",
            "updates": {"rpe": 8},
        }
        blocks = [_make_tool_use_block("modify_exercise_card", tool_input)]
        with _patch_anthropic(blocks):
            result = await parse_transcript("RPE 8 on those")

        assert len(result.raw_tool_calls) == 1
        assert result.raw_tool_calls[0]["name"] == "modify_exercise_card"
        assert result.raw_tool_calls[0]["input"] == tool_input

    async def test_backward_compat_no_modifications_field_defaults_empty(self):
        """Existing tool calls (no modifications) should still work. Modifications defaults to empty."""
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "bench press",
                "sets": [{"reps": 10}],
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("bench press 10 reps")

        assert len(result.exercise_cards) == 1
        assert result.modifications == ()


# ===================================================================
# Integration tests — intent classification + edge cases
# ===================================================================


@pytest.mark.asyncio(loop_scope="session")
class TestIntentClassification:
    """Tests that verify correct intent routing: new vs modify vs observation.

    These test the full parse_transcript() flow with session_context,
    verifying that context is passed through to the API call and that
    the result structure matches the expected intent classification.
    """

    async def test_new_exercise_with_context_present(self):
        """Context has bench press, trainer says 'now squats' — new card, not modify."""
        context = [
            {
                "entry_type": "exercise_card",
                "exercise_name": "bench press",
                "sets": [{"reps": 10, "weight": 80, "weight_unit": "kg"}],
            },
        ]
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "squat",
                "sets": [{"reps": 5, "weight": 100, "weight_unit": "kg"}],
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript(
                "now squats 5 at 100 kilos",
                session_context=context,
            )

        assert len(result.exercise_cards) == 1
        assert result.exercise_cards[0].exercise_name == "squat"
        assert result.modifications == ()

    async def test_modification_with_context(self):
        """Context has bench press, trainer says 'RPE 8 on those' — modify."""
        context = [
            {
                "entry_type": "exercise_card",
                "exercise_name": "bench press",
                "sets": [
                    {"reps": 10, "weight": 80, "weight_unit": "kg"},
                    {"reps": 10, "weight": 80, "weight_unit": "kg"},
                ],
            },
        ]
        blocks = [
            _make_tool_use_block("modify_exercise_card", {
                "target_entry_id": 1,
                "action": "add",
                "updates": {"rpe": 8},
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript(
                "RPE 8 on those",
                session_context=context,
            )

        assert result.exercise_cards == ()
        assert len(result.modifications) == 1
        assert result.modifications[0].target_entry_id == 1

    async def test_observation_with_context_present(self):
        """Context has exercises, trainer says 'he seems tired' — observation, not modify."""
        context = [
            {
                "entry_type": "exercise_card",
                "exercise_name": "bench press",
                "sets": [{"reps": 10, "weight": 80, "weight_unit": "kg"}],
            },
            {
                "entry_type": "exercise_card",
                "exercise_name": "squat",
                "sets": [{"reps": 5, "weight": 100, "weight_unit": "kg"}],
            },
        ]
        blocks = [
            _make_tool_use_block("record_observation_card", {
                "observation_text": "Client appears fatigued, lower energy than usual.",
                "flag_color": "yellow",
                "flag_reason": "unusual fatigue",
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript(
                "he seems really tired today",
                session_context=context,
            )

        assert result.exercise_cards == ()
        assert result.modifications == ()
        assert len(result.observation_cards) == 1

    async def test_empty_context_list_same_as_none(self):
        """session_context=[] should behave identically to session_context=None."""
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "bench press",
                "sets": [{"reps": 10}],
            }),
        ]
        mock_response = _make_mock_response(blocks)
        mock_client = AsyncMock()
        mock_client.messages.create.return_value = mock_response

        with patch(
            "app.services.parser.anthropic.AsyncAnthropic",
            return_value=mock_client,
        ):
            result = await parse_transcript(
                "bench press 10 reps",
                session_context=[],
            )

        # Should send raw transcript, not context block
        user_msg = mock_client.messages.create.call_args.kwargs["messages"][0]["content"]
        assert "Session context" not in user_msg
        assert user_msg == "bench press 10 reps"

    async def test_ambiguous_reference_yellow_flag(self):
        """Context has two bench variations — ambiguous 'the bench' → yellow flag.

        When Claude can't tell which entry the trainer means, it should
        flag the ambiguity rather than guessing (rules 8 + 13).
        """
        context = [
            {
                "entry_type": "exercise_card",
                "exercise_name": "bench press",
                "sets": [{"reps": 10, "weight": 80, "weight_unit": "kg"}],
            },
            {
                "entry_type": "exercise_card",
                "exercise_name": "incline bench press",
                "sets": [{"reps": 12, "weight": 60, "weight_unit": "kg"}],
            },
        ]
        blocks = [
            _make_tool_use_block("record_observation_card", {
                "observation_text": "Trainer said 'RPE 8 on the bench' but context has both bench press and incline bench press — unclear which entry to modify.",
                "flag_color": "yellow",
                "flag_reason": "ambiguous exercise reference",
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript(
                "RPE 8 on the bench",
                session_context=context,
            )

        assert result.modifications == ()
        assert len(result.observation_cards) == 1
        assert result.observation_cards[0].flag_color == "yellow"

    async def test_late_reference_to_early_exercise(self):
        """Trainer refers back to entry [1] after logging several more exercises.

        'Oh by the way, his bench form was shaky on the last set' — should
        still connect to entry [1] even though we're now on entry [5].
        """
        context = [
            {
                "entry_type": "exercise_card",
                "exercise_name": "bench press",
                "sets": [{"reps": 10, "weight": 80, "weight_unit": "kg"}],
            },
            {
                "entry_type": "exercise_card",
                "exercise_name": "squat",
                "sets": [{"reps": 5, "weight": 100, "weight_unit": "kg"}],
            },
            {
                "entry_type": "exercise_card",
                "exercise_name": "overhead press",
                "sets": [{"reps": 8, "weight": 40, "weight_unit": "kg"}],
            },
            {
                "entry_type": "exercise_card",
                "exercise_name": "barbell row",
                "sets": [{"reps": 10, "weight": 60, "weight_unit": "kg"}],
            },
        ]
        blocks = [
            _make_tool_use_block("modify_exercise_card", {
                "target_entry_id": 1,
                "action": "add",
                "form_notes": ["form was shaky on last set"],
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript(
                "oh by the way his bench form was shaky on the last set",
                session_context=context,
            )

        assert len(result.modifications) == 1
        mod = result.modifications[0]
        assert mod.target_entry_id == 1
        assert mod.form_notes == ("form was shaky on last set",)

    async def test_same_exercise_twice_in_session(self):
        """Bench press warm-up [1] and working sets [3]. 'RPE 9 on bench' is ambiguous.

        Two instances of the same exercise name → ambiguous reference → yellow flag.
        """
        context = [
            {
                "entry_type": "exercise_card",
                "exercise_name": "bench press",
                "sets": [{"reps": 10, "weight": 40, "weight_unit": "kg"}],
            },
            {
                "entry_type": "exercise_card",
                "exercise_name": "squat",
                "sets": [{"reps": 5, "weight": 100, "weight_unit": "kg"}],
            },
            {
                "entry_type": "exercise_card",
                "exercise_name": "bench press",
                "sets": [{"reps": 5, "weight": 100, "weight_unit": "kg"}],
            },
        ]
        blocks = [
            _make_tool_use_block("record_observation_card", {
                "observation_text": "Trainer said 'RPE 9 on bench' but there are two bench press entries in the session — unclear which one.",
                "flag_color": "yellow",
                "flag_reason": "ambiguous — two bench press entries in session",
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript(
                "RPE 9 on bench",
                session_context=context,
            )

        assert result.modifications == ()
        assert len(result.observation_cards) == 1
        assert result.observation_cards[0].flag_color == "yellow"

    async def test_all_three_tool_types_in_one_clip(self):
        """One transcript produces a new exercise, a modification, and an observation."""
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "lateral raises",
                "sets": [{"reps": 15, "weight": 10, "weight_unit": "kg"}],
            }, block_id="toolu_1"),
            _make_tool_use_block("modify_exercise_card", {
                "target_entry_id": 1,
                "action": "add",
                "updates": {"rpe": 7},
            }, block_id="toolu_2"),
            _make_tool_use_block("record_observation_card", {
                "observation_text": "Client's energy picking up in the second half.",
                "flag_color": "green",
                "flag_reason": "positive energy trend",
            }, block_id="toolu_3"),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript(
                "lateral raises 15 at 10 kilos also RPE 7 on the bench and he's got more energy now",
                session_context=[{
                    "entry_type": "exercise_card",
                    "exercise_name": "bench press",
                    "sets": [{"reps": 10, "weight": 80, "weight_unit": "kg"}],
                }],
            )

        assert len(result.exercise_cards) == 1
        assert len(result.modifications) == 1
        assert len(result.observation_cards) == 1


# ===================================================================
# Real speech patterns (mocked Claude responses)
# ===================================================================


@pytest.mark.asyncio(loop_scope="session")
class TestRealSpeechPatterns:
    """Each test mocks Claude's expected response for a natural speech transcript
    and verifies our extraction code processes it correctly. These test that
    our dataclass extraction + downstream handling work, not Claude itself."""

    async def test_catch_up_batch_two_sets(self):
        """'bench press, first set 60kg 10 reps, second set 60kg 8 reps' → 1 card, 2 sets."""
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "bench press",
                "sets": [
                    {"reps": 10, "weight": 60, "weight_unit": "kg"},
                    {"reps": 8, "weight": 60, "weight_unit": "kg"},
                ],
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript(
                "bench press, first set 60kg 10 reps, second set 60kg 8 reps"
            )

        assert len(result.exercise_cards) == 1
        assert len(result.exercise_cards[0].sets) == 2
        assert result.exercise_cards[0].sets[0].reps == 10
        assert result.exercise_cards[0].sets[1].reps == 8

    async def test_rir_spoken(self):
        """'squat 5 at 100 kilos RIR 2' → rir=2, rpe=None."""
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "squat",
                "sets": [{"reps": 5, "weight": 100, "weight_unit": "kg", "rir": 2}],
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("squat 5 at 100 kilos RIR 2")

        s = result.exercise_cards[0].sets[0]
        assert s.rir == 2
        assert s.rpe is None  # parser doesn't convert — validation does

    async def test_rir_colloquial(self):
        """'could do about 2 more' with context → modification with rir."""
        blocks = [
            _make_tool_use_block("modify_exercise_card", {
                "target_entry_id": 1,
                "action": "add",
                "updates": {"rir": 2},
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript(
                "could do about 2 more",
                session_context=[{
                    "entry_type": "exercise_card",
                    "exercise_name": "squat",
                    "sets": [{"reps": 5, "weight": 100, "weight_unit": "kg"}],
                }],
            )

        assert len(result.modifications) == 1
        assert result.modifications[0].updates == {"rir": 2}

    async def test_equipment_modification(self):
        """'set 3 with a red band, 60 kilos 6 reps' → equipment_note on set."""
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "squat",
                "sets": [
                    {"reps": 6, "weight": 60, "weight_unit": "kg", "equipment_note": "with a red band"},
                ],
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("set 3 with a red band, 60 kilos 6 reps")

        s = result.exercise_cards[0].sets[0]
        assert s.equipment_note == "with a red band"

    async def test_general_observation_standalone(self):
        """'energy levels are dropping' → standalone observation card."""
        blocks = [
            _make_tool_use_block("record_observation_card", {
                "observation_text": "Client's energy levels are dropping.",
                "flag_color": "yellow",
                "flag_reason": "declining energy",
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("energy levels are dropping")

        assert len(result.exercise_cards) == 0
        assert len(result.observation_cards) == 1
        assert result.observation_cards[0].flag_color == "yellow"

    async def test_structured_correction(self):
        """'correction, change third set from 12 to 8' → modify action='correct'."""
        blocks = [
            _make_tool_use_block("modify_exercise_card", {
                "target_entry_id": 1,
                "action": "correct",
                "target_sets": [3],
                "updates": {"reps": 8},
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript(
                "correction, change third set from 12 to 8",
                session_context=[{
                    "entry_type": "exercise_card",
                    "exercise_name": "bench press",
                    "sets": [
                        {"reps": 10, "weight": 80, "weight_unit": "kg"},
                        {"reps": 10, "weight": 80, "weight_unit": "kg"},
                        {"reps": 12, "weight": 80, "weight_unit": "kg"},
                    ],
                }],
            )

        assert len(result.modifications) == 1
        mod = result.modifications[0]
        assert mod.action == "correct"
        assert mod.target_sets == (3,)
        assert mod.updates == {"reps": 8}

    async def test_mixed_exercise_and_observation(self):
        """'deadlift 3x5 at 140, also right knee clicking' → 1 exercise + 1 observation."""
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "deadlift",
                "sets": [
                    {"reps": 5, "weight": 140, "weight_unit": "kg"},
                    {"reps": 5, "weight": 140, "weight_unit": "kg"},
                    {"reps": 5, "weight": 140, "weight_unit": "kg"},
                ],
            }, block_id="toolu_1"),
            _make_tool_use_block("record_observation_card", {
                "observation_text": "Right knee clicking during deadlifts.",
                "flag_color": "yellow",
                "flag_reason": "knee clicking",
            }, block_id="toolu_2"),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("deadlift 3x5 at 140, also right knee clicking")

        assert len(result.exercise_cards) == 1
        assert len(result.observation_cards) == 1
        assert result.exercise_cards[0].exercise_name == "deadlift"
        assert len(result.exercise_cards[0].sets) == 3

    async def test_minimal_shorthand(self):
        """'bench, 3 by 10, 80 kilos' → 3 sets, 10 reps each."""
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "bench",
                "sets": [
                    {"reps": 10, "weight": 80, "weight_unit": "kg"},
                    {"reps": 10, "weight": 80, "weight_unit": "kg"},
                    {"reps": 10, "weight": 80, "weight_unit": "kg"},
                ],
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("bench, 3 by 10, 80 kilos")

        assert len(result.exercise_cards) == 1
        assert len(result.exercise_cards[0].sets) == 3
        for s in result.exercise_cards[0].sets:
            assert s.reps == 10
            assert s.weight == 80

    async def test_bodyweight_descending_reps(self):
        """'pull-ups, 3 sets, 12, 10, 8 reps' → 3 sets, no weight."""
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "pull-ups",
                "sets": [
                    {"reps": 12},
                    {"reps": 10},
                    {"reps": 8},
                ],
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("pull-ups, 3 sets, 12, 10, 8 reps")

        card = result.exercise_cards[0]
        assert len(card.sets) == 3
        assert card.sets[0].reps == 12
        assert card.sets[1].reps == 10
        assert card.sets[2].reps == 8
        assert all(s.weight is None for s in card.sets)

    async def test_rpe_on_set_range(self):
        """'RPE 8 on sets 2 through 4' with context → modify target_sets=[2,3,4]."""
        blocks = [
            _make_tool_use_block("modify_exercise_card", {
                "target_entry_id": 1,
                "action": "add",
                "target_sets": [2, 3, 4],
                "updates": {"rpe": 8},
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript(
                "RPE 8 on sets 2 through 4",
                session_context=[{
                    "entry_type": "exercise_card",
                    "exercise_name": "squat",
                    "sets": [
                        {"reps": 5, "weight": 100, "weight_unit": "kg"},
                        {"reps": 5, "weight": 100, "weight_unit": "kg"},
                        {"reps": 5, "weight": 100, "weight_unit": "kg"},
                        {"reps": 5, "weight": 100, "weight_unit": "kg"},
                    ],
                }],
            )

        mod = result.modifications[0]
        assert mod.target_sets == (2, 3, 4)
        assert mod.updates == {"rpe": 8}

    async def test_form_and_cues(self):
        """'RDL 4x8 at 60, good hip hinge, told her chest up' → form_notes + cues_given."""
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "RDL",
                "sets": [
                    {"reps": 8, "weight": 60, "weight_unit": "kg"},
                    {"reps": 8, "weight": 60, "weight_unit": "kg"},
                    {"reps": 8, "weight": 60, "weight_unit": "kg"},
                    {"reps": 8, "weight": 60, "weight_unit": "kg"},
                ],
                "form_notes": ["good hip hinge"],
                "cues_given": ["chest up"],
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript(
                "RDL 4x8 at 60, good hip hinge, told her chest up"
            )

        card = result.exercise_cards[0]
        assert "good hip hinge" in card.form_notes
        assert "chest up" in card.cues_given

    async def test_rir_and_equipment_together(self):
        """'squats with a band, 3x10 at 60, RIR 3' → both new fields."""
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "squats",
                "sets": [
                    {"reps": 10, "weight": 60, "weight_unit": "kg", "rir": 3, "equipment_note": "with a band"},
                    {"reps": 10, "weight": 60, "weight_unit": "kg", "rir": 3, "equipment_note": "with a band"},
                    {"reps": 10, "weight": 60, "weight_unit": "kg", "rir": 3, "equipment_note": "with a band"},
                ],
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("squats with a band, 3x10 at 60, RIR 3")

        card = result.exercise_cards[0]
        for s in card.sets:
            assert s.rir == 3
            assert s.equipment_note == "with a band"

    async def test_ambiguous_without_context(self):
        """'add RPE 7 to those' without clear context → yellow flag observation."""
        blocks = [
            _make_tool_use_block("record_observation_card", {
                "observation_text": "Trainer said 'add RPE 7 to those' but no clear exercise reference.",
                "flag_color": "yellow",
                "flag_reason": "ambiguous reference — unclear which exercise",
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript("add RPE 7 to those")

        assert len(result.observation_cards) == 1
        assert result.observation_cards[0].flag_color == "yellow"

    async def test_multi_field_correction(self):
        """'bench was 85 not 80, and add RPE 9' → correction with 2 updates."""
        blocks = [
            _make_tool_use_block("modify_exercise_card", {
                "target_entry_id": 1,
                "action": "correct",
                "updates": {"weight": 85, "weight_unit": "kg", "rpe": 9},
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript(
                "bench was 85 not 80, and add RPE 9",
                session_context=[{
                    "entry_type": "exercise_card",
                    "exercise_name": "bench press",
                    "sets": [{"reps": 10, "weight": 80, "weight_unit": "kg"}],
                }],
            )

        mod = result.modifications[0]
        assert mod.action == "correct"
        assert mod.updates["weight"] == 85
        assert mod.updates["rpe"] == 9

    async def test_additive_set(self):
        """'did one more set of bench, 80 for 5' with context → modification action='add'."""
        blocks = [
            _make_tool_use_block("modify_exercise_card", {
                "target_entry_id": 1,
                "action": "add",
                "updates": {"reps": 5, "weight": 80, "weight_unit": "kg"},
            }),
        ]
        with _patch_anthropic(blocks):
            result = await parse_transcript(
                "did one more set of bench, 80 for 5",
                session_context=[{
                    "entry_type": "exercise_card",
                    "exercise_name": "bench press",
                    "sets": [
                        {"reps": 10, "weight": 80, "weight_unit": "kg"},
                        {"reps": 10, "weight": 80, "weight_unit": "kg"},
                        {"reps": 10, "weight": 80, "weight_unit": "kg"},
                    ],
                }],
            )

        assert len(result.modifications) == 1
        assert result.modifications[0].action == "add"


# ===================================================================
# Parser edge cases — robustness against malformed Claude responses
# ===================================================================


class TestParserEdgeCases:
    """Tests for _build_exercise_card and _extract_parser_result handling
    of malformed or unexpected data from Claude's tool_use responses."""

    def test_null_set_in_array_skipped(self):
        """Claude returns [set_dict, null, set_dict] — nulls skipped cleanly."""
        tool_input = {
            "exercise_name": "bench press",
            "sets": [
                {"reps": 10, "weight": 80, "weight_unit": "kg"},
                None,
                {"reps": 8, "weight": 80, "weight_unit": "kg"},
            ],
        }
        card = _build_exercise_card(tool_input)
        assert card.exercise_name == "bench press"
        assert card.sets is not None
        assert len(card.sets) == 2
        assert card.sets[0].reps == 10
        assert card.sets[1].reps == 8

    def test_empty_sets_array(self):
        """Claude returns 'sets': [] — card created with sets=None, no crash."""
        tool_input = {
            "exercise_name": "pull-ups",
            "sets": [],
        }
        card = _build_exercise_card(tool_input)
        assert card.exercise_name == "pull-ups"
        assert card.sets is None

    def test_set_missing_reps_skipped(self):
        """Set dict without 'reps' key — skipped, valid sets preserved."""
        tool_input = {
            "exercise_name": "squat",
            "sets": [
                {"reps": 5, "weight": 100, "weight_unit": "kg"},
                {"weight": 100, "weight_unit": "kg"},  # missing reps
                {"reps": 5, "weight": 100, "weight_unit": "kg"},
            ],
        }
        card = _build_exercise_card(tool_input)
        assert card.sets is not None
        assert len(card.sets) == 2

    def test_equipment_note_in_modification(self):
        """modify_exercise_card with equipment_note in updates flows through."""
        blocks = [
            _make_tool_use_block("modify_exercise_card", {
                "target_entry_id": 1,
                "action": "add",
                "target_sets": [3],
                "updates": {"equipment_note": "with chains"},
            }),
        ]
        result = _extract_parser_result(blocks)
        assert len(result.modifications) == 1
        mod = result.modifications[0]
        assert mod.updates["equipment_note"] == "with chains"
        assert mod.target_sets == (3,)

    def test_rir_in_modification(self):
        """modify_exercise_card with rir in updates flows through."""
        blocks = [
            _make_tool_use_block("modify_exercise_card", {
                "target_entry_id": 1,
                "action": "add",
                "updates": {"rir": 2},
            }),
        ]
        result = _extract_parser_result(blocks)
        assert len(result.modifications) == 1
        assert result.modifications[0].updates["rir"] == 2

    def test_multiple_tool_calls_mixed_types(self):
        """Response with all 3 tool types — exercise, observation, modification."""
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "bench press",
                "sets": [{"reps": 10, "weight": 80, "weight_unit": "kg"}],
            }, block_id="toolu_1"),
            _make_tool_use_block("record_observation_card", {
                "observation_text": "Client energy low today",
                "flag_color": "yellow",
                "flag_reason": "Low energy reported",
            }, block_id="toolu_2"),
            _make_tool_use_block("modify_exercise_card", {
                "target_entry_id": 1,
                "action": "add",
                "updates": {"rpe": 8},
            }, block_id="toolu_3"),
        ]
        result = _extract_parser_result(blocks)
        assert len(result.exercise_cards) == 1
        assert len(result.observation_cards) == 1
        assert len(result.modifications) == 1
        assert len(result.raw_tool_calls) == 3

    def test_unknown_tool_name_ignored(self):
        """Claude calls a tool name we don't recognize — skip it, don't crash."""
        blocks = [
            _make_tool_use_block("record_exercise_card", {
                "exercise_name": "squat",
            }, block_id="toolu_1"),
            _make_tool_use_block("record_nutrition_log", {
                "food": "banana",
            }, block_id="toolu_2"),
        ]
        result = _extract_parser_result(blocks)
        assert len(result.exercise_cards) == 1
        assert len(result.observation_cards) == 0
        assert len(result.modifications) == 0
        # Unknown tool still captured in raw_tool_calls for debugging
        assert len(result.raw_tool_calls) == 2


# ===================================================================
# Observation card — set-level attachment
# ===================================================================


class TestObservationCardAttachment:
    """Tests for target_entry_id and attached_to_set on observation cards."""

    def test_tool_schema_has_attachment_fields(self):
        """observation_card tool schema includes target_entry_id and attached_to_set."""
        props = OBSERVATION_CARD_TOOL["input_schema"]["properties"]
        assert "target_entry_id" in props
        assert props["target_entry_id"]["type"] == "integer"
        assert "attached_to_set" in props
        assert props["attached_to_set"]["type"] == "integer"
        # Neither should be required
        required = OBSERVATION_CARD_TOOL["input_schema"]["required"]
        assert "target_entry_id" not in required
        assert "attached_to_set" not in required

    def test_build_observation_card_with_both_fields(self):
        """_build_observation_card extracts target_entry_id + attached_to_set."""
        card = _build_observation_card({
            "observation_text": "Left weaker than right on clamshells",
            "target_entry_id": 1,
            "attached_to_set": 2,
        })
        assert card.observation_text == "Left weaker than right on clamshells"
        assert card.target_entry_id == 1
        assert card.attached_to_set == 2

    def test_build_observation_card_target_only(self):
        """Exercise-level observation: target_entry_id set, attached_to_set omitted."""
        card = _build_observation_card({
            "observation_text": "Form breakdown on deadlift",
            "target_entry_id": 3,
        })
        assert card.target_entry_id == 3
        assert card.attached_to_set is None

    def test_build_observation_card_no_attachment(self):
        """Session-level observation: both fields omitted (backward compat)."""
        card = _build_observation_card({
            "observation_text": "Client energy dropping",
            "flag_color": "yellow",
            "flag_reason": "fatigue",
        })
        assert card.target_entry_id is None
        assert card.attached_to_set is None
        assert card.flag_color == "yellow"

    def test_extract_parser_result_preserves_attachment(self):
        """_extract_parser_result passes attachment fields through."""
        blocks = [
            _make_tool_use_block("record_observation_card", {
                "observation_text": "Left is tougher than right",
                "target_entry_id": 1,
                "attached_to_set": 1,
            }),
        ]
        result = _extract_parser_result(blocks)
        assert len(result.observation_cards) == 1
        card = result.observation_cards[0]
        assert card.target_entry_id == 1
        assert card.attached_to_set == 1

    def test_context_format_observation_with_set_attachment(self):
        """Observation with attached_to_set shows '(set N)' in context."""
        entries = [
            {
                "entry_type": "observation_card",
                "observation_text": "Left weaker than right",
                "attached_to_set": 2,
            },
        ]
        result = format_session_context(entries)
        assert "[1] Observation: Left weaker than right (set 2)" in result

    def test_context_format_observation_without_attachment(self):
        """Observation without attached_to_set shows no set annotation."""
        entries = [
            {
                "entry_type": "observation_card",
                "observation_text": "Energy dropping",
            },
        ]
        result = format_session_context(entries)
        assert "(set " not in result
        assert "[1] Observation: Energy dropping" in result
