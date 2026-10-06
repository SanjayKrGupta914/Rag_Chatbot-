"""
Unit tests for Gemini fallback integration in PDF Text Extractor
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from llm_service import OllamaService, GeminiService, HybridLLMService, LLMResponse
from query_handler import QueryHandler


class TestGeminiFallback(unittest.TestCase):

    def test_gemini_service_health_check_without_key(self):
        """GeminiService health_check returns False if API key is not present."""
        service = GeminiService(api_key="")
        self.assertFalse(service.health_check())

    def test_gemini_service_health_check_with_key(self):
        """GeminiService health_check returns True if API key is present."""
        service = GeminiService(api_key="fake-test-key")
        self.assertTrue(service.health_check())

    @patch("llm_service.requests.Session.post")
    def test_gemini_service_generate_response_rest(self, mock_post):
        """GeminiService generate_response succeeds via REST API."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Gemini answer content"}]
                    }
                }
            ],
            "usageMetadata": {"candidatesTokenCount": 10}
        }
        mock_post.return_value = mock_response

        service = GeminiService(api_key="fake-test-key", model="gemini-2.5-flash")
        res = service.generate_response("Test prompt", system_instruction="System rule")

        self.assertTrue(res.success)
        self.assertEqual(res.response, "Gemini answer content")
        self.assertEqual(res.provider, "gemini")

    @patch.object(OllamaService, "health_check", return_value=True)
    @patch.object(OllamaService, "generate_response")
    def test_hybrid_service_uses_ollama_when_available(self, mock_ollama_gen, mock_ollama_health):
        """HybridLLMService prefers Ollama when healthy and working."""
        mock_ollama_gen.return_value = LLMResponse(
            success=True,
            response="Ollama answer",
            model="llama2",
            provider="ollama"
        )

        hybrid = HybridLLMService(
            ollama_url="http://localhost:11434",
            ollama_model="llama2",
            gemini_api_key="fake-key",
            enable_gemini_fallback=True
        )

        res = hybrid.generate_response("Question prompt")
        self.assertTrue(res.success)
        self.assertEqual(res.response, "Ollama answer")
        self.assertEqual(res.provider, "ollama")

    @patch.object(OllamaService, "health_check", return_value=False)
    @patch.object(GeminiService, "health_check", return_value=True)
    @patch.object(GeminiService, "generate_response")
    def test_hybrid_service_falls_back_to_gemini_when_ollama_offline(
        self, mock_gemini_gen, mock_gemini_health, mock_ollama_health
    ):
        """HybridLLMService falls back to Gemini when Ollama is offline."""
        mock_gemini_gen.return_value = LLMResponse(
            success=True,
            response="Gemini fallback answer",
            model="gemini-2.5-flash",
            provider="gemini"
        )

        hybrid = HybridLLMService(
            ollama_url="http://localhost:11434",
            ollama_model="llama2",
            gemini_api_key="fake-key",
            enable_gemini_fallback=True
        )

        res = hybrid.generate_response("Question prompt")
        self.assertTrue(res.success)
        self.assertEqual(res.response, "Gemini fallback answer")
        self.assertIn("Gemini Fallback", res.model)

    @patch.object(OllamaService, "health_check", return_value=True)
    @patch.object(OllamaService, "generate_response")
    @patch.object(GeminiService, "health_check", return_value=True)
    @patch.object(GeminiService, "generate_response")
    def test_hybrid_service_falls_back_to_gemini_when_ollama_fails(
        self, mock_gemini_gen, mock_gemini_health, mock_ollama_gen, mock_ollama_health
    ):
        """HybridLLMService falls back to Gemini if Ollama generation fails with error."""
        mock_ollama_gen.return_value = LLMResponse(
            success=False,
            error="Ollama HTTP 500",
            model="llama2",
            provider="ollama"
        )
        mock_gemini_gen.return_value = LLMResponse(
            success=True,
            response="Gemini fallback answer after Ollama error",
            model="gemini-2.5-flash",
            provider="gemini"
        )

        hybrid = HybridLLMService(
            ollama_url="http://localhost:11434",
            ollama_model="llama2",
            gemini_api_key="fake-key",
            enable_gemini_fallback=True
        )

        res = hybrid.generate_response("Question prompt")
        self.assertTrue(res.success)
        self.assertEqual(res.response, "Gemini fallback answer after Ollama error")

    @patch.object(HybridLLMService, "health_check", return_value=True)
    @patch.object(HybridLLMService, "generate_response")
    def test_query_handler_uses_hybrid_service(self, mock_generate, mock_health):
        """QueryHandler uses HybridLLMService and returns QueryResult."""
        mock_generate.return_value = LLMResponse(
            success=True,
            response="Extracted document answer",
            model="gemini-2.5-flash (Gemini Fallback)",
            provider="gemini"
        )

        handler = QueryHandler(gemini_api_key="fake-key")
        result = handler.answer_question("PDF document context text", "What is the content?")

        self.assertTrue(result.success)
        self.assertEqual(result.answer, "Extracted document answer")
        self.assertIn("gemini", result.model_used.lower())


if __name__ == "__main__":
    unittest.main()
