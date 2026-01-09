"""Vision analysis module using Claude to extract entities and relations from images."""

import json
import os
from dataclasses import dataclass, field
from typing import Any

import anthropic

from .video_processor import FrameData


@dataclass
class EntityData:
    """Extracted entity from scene."""
    id: str
    type: str
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class RelationData:
    """Extracted relation between entities."""
    type: str
    from_entity: str
    to_entity: str
    roles: dict[str, str] = field(default_factory=dict)


@dataclass
class SchemaChange:
    """Proposed schema change."""
    change_type: str  # "new_entity_type", "new_attribute_type", "new_relation_type", "modified_type"
    definition: dict[str, Any]


@dataclass
class AnalysisResult:
    """Complete analysis result from vision analyzer."""
    # Data that fits existing schema
    new_entities: list[EntityData] = field(default_factory=list)
    new_relations: list[RelationData] = field(default_factory=list)

    # Schema changes needed
    schema_changes: list[SchemaChange] = field(default_factory=list)

    # Data that requires schema changes first
    pending_entities: list[EntityData] = field(default_factory=list)
    pending_relations: list[RelationData] = field(default_factory=list)

    # Raw response for debugging
    raw_response: dict[str, Any] | None = None


SCENE_ANALYSIS_PROMPT = """You are analyzing a scene to extract entities, attributes, and SPATIAL RELATIONS for a knowledge graph stored in TypeDB.

CURRENT SCHEMA:
{schema}

INSTRUCTIONS:
1. Identify all objects/entities in the image(s)
2. For each entity, determine:
   - If it fits an existing type in the schema -> add to "new_data"
   - If it requires a new type or schema change -> add to "schema_changes" and "data_requiring_schema_change"

3. For attributes:
   - Use existing attribute types where applicable
   - Propose new attributes only when necessary
   - Common attributes: name, color, material, size, shape, position_description

4. For RELATIONS (CRITICAL - DO NOT SKIP):
   RELATIONS are as important as entities! Carefully identify spatial relationships between objects.

   Common spatial relations to look for:
   - on: object is placed on top of a surface (laptop on desk, cup on table)
   - under: object is underneath another (box under table, tower under desk)
   - next_to: objects are adjacent/beside each other (chair next to desk)
   - in_front_of: object is in front of another from viewer perspective
   - behind: object is behind another
   - inside/contains: object is contained within another (items in box, books in shelf)
   - attached_to: object is physically attached (lamp attached to wall)
   - sits_in/sitting_on: person is sitting in/on furniture

   For EACH relation:
   - Specify: type, from (subject entity ID), to (reference entity ID)
   - Use existing relation types when available in schema
   - If new relation type needed, define it in schema_changes as a subtype of spatial_relation (this inherits the standard subject/reference roles)

   EXAMPLES of good relations:
   - laptop on desk: {{"type": "on", "from": "laptop_1", "to": "desk_main"}}
   - person sits in chair: {{"type": "sitting_on", "from": "person_1", "to": "chair_1"}}
   - monitor next to monitor: {{"type": "next_to", "from": "monitor_1", "to": "monitor_2"}}

5. Entity IDs should be descriptive like "chair_1", "table_main", "lamp_desk"

RETURN VALID JSON with this exact structure:
{{
  "new_data": {{
    "entities": [
      {{"id": "unique_id", "type": "existing_type", "attributes": {{"color": "brown", "material": "wood"}}}}
    ],
    "relations": [
      {{"type": "existing_relation", "from": "entity_id", "to": "entity_id"}}
    ]
  }},
  "schema_changes": {{
    "new_entity_types": [
      {{"name": "type_name", "parent": "entity", "owns": ["attr1", "attr2"]}}
    ],
    "new_attribute_types": [
      {{"name": "attr_name", "value_type": "string"}}
    ],
    "new_relation_types": [
      {{"name": "relation_name", "parent": "spatial_relation"}}
    ],
    "modified_types": [
      {{"name": "existing_type", "add_owns": ["new_attr"], "add_plays": ["new_role"]}}
    ]
  }},
  "data_requiring_schema_change": {{
    "entities": [
      {{"id": "new_entity_id", "type": "new_type", "attributes": {{}}}}
    ],
    "relations": [
      {{"type": "new_relation_type", "from": "entity_id", "to": "entity_id"}}
    ]
  }}
}}

IMPORTANT REMINDERS:
- Extract ALL visible spatial relationships between objects
- Relations are mandatory - every scene should have multiple relations
- Common scene patterns:
  * Objects ON surfaces (monitors on desk, cups on table)
  * People SITTING in/on furniture
  * Objects NEXT TO each other
  * Objects UNDER surfaces (computer tower under desk)
- If you identify 10 entities, you should identify at least 5-10 relations

Be thorough but only include objects and relations you can clearly identify. Be conservative with schema changes - reuse existing types when reasonable.
Return ONLY valid JSON, no other text."""


class VisionAnalyzer:
    """Analyze images using Claude's vision capabilities."""

    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-20250514", debug: bool = False):
        """
        Initialize vision analyzer.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Claude model to use for analysis
            debug: Enable verbose debug logging
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.client = None
        self.model = model
        self.debug = debug

    def _ensure_client(self):
        """Lazy initialization of Anthropic client."""
        if self.client is None:
            if not self.api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY environment variable is required for vision analysis.\n"
                    "Set it with: export ANTHROPIC_API_KEY=your_key_here"
                )
            self.client = anthropic.Anthropic(api_key=self.api_key)

    def analyze_frames(
        self,
        frames: list[FrameData],
        current_schema: str | None = None
    ) -> AnalysisResult:
        """
        Analyze video frames to extract entities and relations.

        Args:
            frames: List of frames to analyze
            current_schema: Current TypeDB schema (None for first scene)

        Returns:
            AnalysisResult with extracted data and schema changes
        """
        self._ensure_client()

        schema_text = current_schema if current_schema else "No existing schema (this is the first scene). Define all needed types."

        prompt = SCENE_ANALYSIS_PROMPT.format(schema=schema_text)

        # Build message content with images
        content = []

        # Add images
        for i, frame in enumerate(frames):
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": frame.image_base64
                }
            })
            if len(frames) > 1:
                content.append({
                    "type": "text",
                    "text": f"[Frame {i + 1} at {frame.timestamp_sec:.1f}s]"
                })

        # Add the analysis prompt
        content.append({
            "type": "text",
            "text": prompt
        })

        if self.debug:
            print("\n" + "="*80)
            print("DEBUG: VISION ANALYZER - PROMPT TO CLAUDE")
            print("="*80)
            print(f"Model: {self.model}")
            print(f"Max tokens: 4096")
            print(f"Number of images: {len(frames)}")
            print("\nPrompt text:")
            print(prompt)
            print("="*80 + "\n")

        # Call Claude API
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[
                {"role": "user", "content": content}
            ]
        )

        # Parse response
        response_text = response.content[0].text

        if self.debug:
            print("\n" + "="*80)
            print("DEBUG: VISION ANALYZER - RESPONSE FROM CLAUDE")
            print("="*80)
            print(f"Stop reason: {response.stop_reason}")
            print(f"Usage: {response.usage}")
            print("\nResponse text:")
            print(response_text)
            print("="*80 + "\n")

        try:
            # Try to extract JSON from response
            data = self._parse_json_response(response_text)
            return self._build_analysis_result(data)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            # Return empty result with raw response for debugging
            return AnalysisResult(raw_response={"error": str(e), "text": response_text})

    def _parse_json_response(self, text: str) -> dict:
        """Extract and parse JSON from response text."""
        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON block
        start = text.find('{')
        end = text.rfind('}') + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])

        raise json.JSONDecodeError("No valid JSON found", text, 0)

    def _build_analysis_result(self, data: dict) -> AnalysisResult:
        """Build AnalysisResult from parsed JSON."""
        result = AnalysisResult(raw_response=data)

        # Parse new_data
        new_data = data.get("new_data", {})

        for entity in new_data.get("entities", []):
            result.new_entities.append(EntityData(
                id=entity["id"],
                type=entity["type"],
                attributes=entity.get("attributes", {})
            ))

        for relation in new_data.get("relations", []):
            result.new_relations.append(RelationData(
                type=relation["type"],
                from_entity=relation["from"],
                to_entity=relation["to"],
                roles=relation.get("roles", {})
            ))

        # Parse schema_changes
        schema_changes = data.get("schema_changes", {})

        for entity_type in schema_changes.get("new_entity_types", []):
            result.schema_changes.append(SchemaChange(
                change_type="new_entity_type",
                definition=entity_type
            ))

        for attr_type in schema_changes.get("new_attribute_types", []):
            result.schema_changes.append(SchemaChange(
                change_type="new_attribute_type",
                definition=attr_type
            ))

        for rel_type in schema_changes.get("new_relation_types", []):
            result.schema_changes.append(SchemaChange(
                change_type="new_relation_type",
                definition=rel_type
            ))

        for mod_type in schema_changes.get("modified_types", []):
            result.schema_changes.append(SchemaChange(
                change_type="modified_type",
                definition=mod_type
            ))

        # Parse data_requiring_schema_change
        pending_data = data.get("data_requiring_schema_change", [])

        # Handle both old format (list) and new format (dict with entities/relations)
        if isinstance(pending_data, dict):
            # New format with entities and relations
            for entity in pending_data.get("entities", []):
                result.pending_entities.append(EntityData(
                    id=entity["id"],
                    type=entity["type"],
                    attributes=entity.get("attributes", {})
                ))

            for relation in pending_data.get("relations", []):
                result.pending_relations.append(RelationData(
                    type=relation["type"],
                    from_entity=relation["from"],
                    to_entity=relation["to"],
                    roles=relation.get("roles", {})
                ))
        else:
            # Old format (list of entities only) - for backward compatibility
            for entity in pending_data:
                result.pending_entities.append(EntityData(
                    id=entity["id"],
                    type=entity["type"],
                    attributes=entity.get("attributes", {})
                ))

        return result

    def analyze_single_image(
        self,
        image_base64: str,
        current_schema: str | None = None
    ) -> AnalysisResult:
        """
        Analyze a single image.

        Args:
            image_base64: Base64-encoded image
            current_schema: Current TypeDB schema

        Returns:
            AnalysisResult
        """
        frame = FrameData(
            frame_number=0,
            timestamp_sec=0,
            image_base64=image_base64,
            width=0,
            height=0
        )
        return self.analyze_frames([frame], current_schema)
