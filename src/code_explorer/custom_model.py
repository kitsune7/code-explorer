"""
Custom InferenceClientModel that fixes tool_choice parameter for Qwen models
"""
from smolagents import InferenceClientModel
from smolagents.tools import Tool
from smolagents.models import ChatMessage


class QwenInferenceClientModel(InferenceClientModel):
    """
    Custom InferenceClientModel for Qwen models that fixes the tool_choice parameter.
    Qwen models only support "auto" and "none" for tool_choice, not "required".
    """
    
    def _prepare_completion_kwargs(
        self,
        messages: list[ChatMessage | dict],
        stop_sequences: list[str] | None = None,
        response_format: dict[str, str] | None = None,
        tools_to_call_from: list[Tool] | None = None,
        custom_role_conversions: dict[str, str] | None = None,
        convert_images_to_image_urls: bool = False,
        tool_choice: str | dict | None = "auto",  # Changed from "required" to "auto"
        **kwargs,
    ) -> dict:
        # Override tool_choice to always be "auto" for Qwen models
        if tools_to_call_from:
            tool_choice = "auto"
        
        return super()._prepare_completion_kwargs(
            messages=messages,
            stop_sequences=stop_sequences,
            response_format=response_format,
            tools_to_call_from=tools_to_call_from,
            custom_role_conversions=custom_role_conversions,
            convert_images_to_image_urls=convert_images_to_image_urls,
            tool_choice=tool_choice,
            **kwargs,
        )
