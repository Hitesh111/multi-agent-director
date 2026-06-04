from django.test import SimpleTestCase
from llm.image_gen import extract_prompt, _clean_prompt


class ExtractPromptTests(SimpleTestCase):
    def test_extract_with_asterisks_around_text(self):
        text = "**Scene:** A dark forest.\n\n**IMAGE PROMPT:**\nMoonlit forest with wolves."
        result = extract_prompt(text)
        self.assertEqual(result, "Moonlit forest with wolves.")

    def test_extract_with_asterisk_after_colon(self):
        text = "**Scene:** Dark forest.\n\n**IMAGE PROMPT:**  \nMoonlit forest with raven."
        result = extract_prompt(text)
        self.assertEqual(result, "Moonlit forest with raven.")

    def test_extract_without_asterisks(self):
        text = "Scene description.\nIMAGE PROMPT: A castle on a hill."
        result = extract_prompt(text)
        self.assertEqual(result, "A castle on a hill.")

    def test_extract_case_insensitive(self):
        text = "Some text.\nimage prompt: a dragon flying."
        result = extract_prompt(text)
        self.assertEqual(result, "a dragon flying.")

    def test_extract_no_match(self):
        text = "Just a regular response with no image prompt."
        result = extract_prompt(text)
        self.assertIsNone(result)

    def test_extract_with_colon_and_asterisks(self):
        text = "**IMAGE PROMPT:**a pirate ship."
        result = extract_prompt(text)
        self.assertEqual(result, "a pirate ship.")

    def test_clean_prompt_removes_markdown(self):
        result = _clean_prompt("**bold description**")
        self.assertEqual(result, "bold description")

    def test_clean_prompt_truncates_long(self):
        long = "a" * 250
        result = _clean_prompt(long)
        self.assertEqual(len(result), 200)
        self.assertTrue(result.endswith("..."))

    def test_clean_prompt_strips_quotes(self):
        result = _clean_prompt('"quoted prompt"')
        self.assertEqual(result, "quoted prompt")
