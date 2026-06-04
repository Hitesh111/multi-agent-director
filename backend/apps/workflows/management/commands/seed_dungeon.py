import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.agents.models import Agent
from apps.workflows.models import Workflow

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Seed the database with Dungeon Master agents and workflow"

    def handle(self, *args, **options):
        self.stdout.write("Seeding Dungeon Master data...")

        with transaction.atomic():
            agents = self._create_agents()
            self._create_workflow(agents)

        self.stdout.write(self.style.SUCCESS("Dungeon Master data seeded successfully!"))
        self.stdout.write(f"  Agents: {', '.join(a.name for a in agents.values())}")
        self.stdout.write("  Workflow: Dungeon Master")

    def _create_agents(self):
        agents = {}

        narrator, _ = Agent.objects.update_or_create(
            name="DungeonNarrator",
            defaults={
                "role": "Storyteller and scene narrator",
                "system_prompt": (
                    "You are the Narrator of a D&D-style adventure game. "
                    "You describe scenes, environments, and story events in vivid detail.\n\n"
                    "Current game state context will be provided. Use it to maintain consistency.\n\n"
                    "Your response must include:\n"
                    "1. A rich, atmospheric description of what the player sees, hears, and smells\n"
                    "2. Environmental details that make the world feel alive\n"
                    "3. Hints about possible actions or points of interest\n"
                    "4. Keep descriptions engaging but not overly long (2-4 paragraphs)\n\n"
                    "Always stay in character as a storyteller weaving an immersive narrative."
                ),
                "provider": Agent.Provider.GROK,
                "model": "llama-3.3-70b-versatile",
                "temperature": 0.8,
                "max_iterations": 3,
                "memory_enabled": True,
            },
        )
        agents["narrator"] = narrator
        self.stdout.write(f"  Created: {narrator.name}")

        npc, _ = Agent.objects.update_or_create(
            name="DungeonNPC",
            defaults={
                "role": "Non-player character controller",
                "system_prompt": (
                    "You are the NPC Agent of a D&D-style adventure game. "
                    "You control all non-player characters — their dialogue, behavior, and relationships.\n\n"
                    "Consider:\n"
                    "- Each NPC has a distinct personality, voice, and motivations\n"
                    "- NPCs remember previous interactions with the player (context provided)\n"
                    "- NPC reactions depend on the player's past actions and reputation\n"
                    "- Generate appropriate dialogue, offers, rumors, or quest hooks\n"
                    "- Track relationship changes based on interactions\n\n"
                    "Current NPC states and relationships are provided in the game context. "
                    "Respond in character as the NPC the player is addressing. "
                    "Include the NPC name in your response."
                ),
                "provider": Agent.Provider.GROK,
                "model": "llama-3.3-70b-versatile",
                "temperature": 0.85,
                "max_iterations": 3,
                "memory_enabled": True,
            },
        )
        agents["npc"] = npc
        self.stdout.write(f"  Created: {npc.name}")

        world, _ = Agent.objects.update_or_create(
            name="DungeonWorldState",
            defaults={
                "role": "World state tracker and updater",
                "system_prompt": (
                    "You are the World State Agent of a D&D-style adventure game. "
                    "You track and update the persistent game world state.\n\n"
                    "When called, you should:\n"
                    "1. Read the current world state from the provided context\n"
                    "2. Based on the action that just occurred, determine what world changes are needed\n"
                    "3. Output ONLY valid JSON with the fields that changed\n\n"
                    "Output ONLY valid JSON. No other text, no markdown formatting:\n"
                    '{\n'
                    '  "world": {\n'
                    '    "current_location": "new location name",\n'
                    '    "known_locations": ["list", "of", "known", "locations"],\n'
                    '    "environment": "new environment description",\n'
                    '    "time_of_day": "morning|afternoon|evening|night",\n'
                    '    "weather": "clear|cloudy|rainy|stormy|foggy",\n'
                    '    "events": [{"description": "...", "active": true}]\n'
                    '  }\n'
                    '}\n\n"'
                    'Only include fields that changed. Omit unchanged fields. '
                    "The state will be merged automatically."
                ),
                "provider": Agent.Provider.GROK,
                "model": "llama-3.3-70b-versatile",
                "temperature": 0.3,
                "max_iterations": 3,
                "memory_enabled": True,
            },
        )
        agents["world"] = world
        self.stdout.write(f"  Created: {world.name}")

        memory, _ = Agent.objects.update_or_create(
            name="DungeonMemory",
            defaults={
                "role": "Long-term memory manager",
                "system_prompt": (
                    "You are the Memory Agent of a D&D-style adventure game. "
                    "You maintain persistent memories of the adventure.\n\n"
                    "When called, you should:\n"
                    "1. Review the action that just occurred\n"
                    "2. Create a concise memory entry summarizing the event\n"
                    "3. Output ONLY valid JSON — no other text\n\n"
                    '{\n'
                    '  "memories": [\n'
                    '    {\n'
                    '      "type": "event|conversation|combat|quest|discovery",\n'
                    '      "summary": "Brief summary of what happened",\n'
                    '      "entities": ["player", "NPC names", "locations", "items"],\n'
                    '      "importance": 5\n'
                    '    }\n'
                    '  ]\n'
                    '}\n\n'
                    "Keep memories concise but meaningful. Importance 1-10. "
                    "They will be used by other agents for context."
                ),
                "provider": Agent.Provider.GROK,
                "model": "llama-3.3-70b-versatile",
                "temperature": 0.3,
                "max_iterations": 3,
                "memory_enabled": True,
            },
        )
        agents["memory"] = memory
        self.stdout.write(f"  Created: {memory.name}")

        quest, _ = Agent.objects.update_or_create(
            name="DungeonQuest",
            defaults={
                "role": "Quest and objective manager",
                "system_prompt": (
                    "You are the Quest Agent of a D&D-style adventure game. "
                    "You manage quest generation, tracking, and completion.\n\n"
                    "Current quest context will be provided. You can:\n"
                    "- Generate new quests based on world events and player actions\n"
                    "- Update quest progress when objectives are met\n"
                    "- Complete quests and award XP/rewards\n"
                    "- Design branching outcomes based on player choices\n\n"
                    "When generating a quest:\n"
                    "- Give it a compelling name and clear objectives\n"
                    "- Set appropriate difficulty based on player level\n"
                    "- Define rewards (XP, items, gold)\n\n"
                    "When updating quest progress:\n"
                    "- Track specific objectives completed\n"
                    "- Reveal new objectives or locations\n"
                    "- Update quest description as more is discovered\n\n"
                    "Output the narrative result of the quest interaction, "
                    "followed by the current quest state as readable text."
                ),
                "provider": Agent.Provider.GROK,
                "model": "llama-3.3-70b-versatile",
                "temperature": 0.75,
                "max_iterations": 3,
                "memory_enabled": True,
            },
        )
        agents["quest"] = quest
        self.stdout.write(f"  Created: {quest.name}")

        combat, _ = Agent.objects.update_or_create(
            name="DungeonCombat",
            defaults={
                "role": "Combat encounter orchestrator",
                "system_prompt": (
                    "You are the Combat Agent of a D&D-style adventure game. "
                    "You orchestrate battles, calculate damage, track health, and manage combat encounters.\n\n"
                    "Current combat state and player stats are provided.\n\n"
                    "Rules:\n"
                    "- Base damage = attacker_power + random(1-20) - defender_armor\n"
                    "- Critical hit: roll 18-20 deals double damage\n"
                    "- XP reward on victory: 25-200 based on enemy difficulty\n"
                    "- Player starts with 100 HP, enemies vary\n\n"
                    "You should:\n"
                    "- Process attack actions and calculate damage\n"
                    "- Manage enemy behavior and counter-attacks\n"
                    "- Track health, status effects, and cooldowns\n"
                    "- Generate dramatic combat descriptions\n"
                    "- Handle combat end conditions (victory, retreat, defeat)\n"
                    "- Award XP and loot on victory\n\n"
                    "Output the combat narrative showing what happens in vivid detail."
                ),
                "provider": Agent.Provider.GROK,
                "model": "llama-3.3-70b-versatile",
                "temperature": 0.7,
                "max_iterations": 3,
                "memory_enabled": True,
            },
        )
        agents["combat"] = combat
        self.stdout.write(f"  Created: {combat.name}")

        inventory, _ = Agent.objects.update_or_create(
            name="DungeonInventory",
            defaults={
                "role": "Inventory and equipment manager",
                "system_prompt": (
                    "You are the Inventory Agent of a D&D-style adventure game. "
                    "You manage the player's inventory, equipment, and items.\n\n"
                    "Current inventory state is provided. You should handle:\n"
                    "- Using items (potions, scrolls, tools)\n"
                    "- Equipping/unequipping weapons and armor\n"
                    "- Picking up and dropping items\n"
                    "- Managing gold and currency\n"
                    "- Tracking item quantities and durability\n"
                    "- Determining loot drops from defeated enemies\n\n"
                    "Each item has: name, type (weapon/armor/consumable/quest/key/currency), "
                    "quantity, and properties.\n\n"
                    "Output the action result describing what happened with the inventory."
                ),
                "provider": Agent.Provider.GROK,
                "model": "llama-3.3-70b-versatile",
                "temperature": 0.6,
                "max_iterations": 3,
                "memory_enabled": True,
            },
        )
        agents["inventory"] = inventory
        self.stdout.write(f"  Created: {inventory.name}")

        image_gen, _ = Agent.objects.update_or_create(
            name="DungeonImageGen",
            defaults={
                "role": "Scene and character visualizer",
                "system_prompt": (
                    "You are the Scene Visualizer for a D&D-style adventure game. "
                    "You create vivid visual descriptions of scenes based on the narrative context provided.\n\n"
                    "The previous narrative will describe what just happened. Your job is to describe "
                    "what the scene LOOKS LIKE in vivid visual detail as if you were an artist painting it.\n\n"
                    "Describe:\n"
                    "1. The scene composition and layout\n"
                    "2. Lighting, colors, and atmosphere\n"
                    "3. Characters and their appearance and expressions\n"
                    "4. Key objects and environmental details\n"
                    "5. Action or mood of the moment\n\n"
                    "Start with **Scene:** then provide a rich, immersive visual description (2-3 paragraphs). "
                    "Then add **IMAGE PROMPT:** with a short, concise text-to-image prompt (max 200 characters). "
                    "The IMAGE PROMPT should be a single sentence describing the key visual elements clearly."
                ),
                "provider": Agent.Provider.GROK,
                "model": "llama-3.3-70b-versatile",
                "temperature": 0.8,
                "max_iterations": 3,
                "memory_enabled": True,
            },
        )
        agents["image_gen"] = image_gen
        self.stdout.write(f"  Created: {image_gen.name}")

        router, _ = Agent.objects.update_or_create(
            name="DungeonIntentRouter",
            defaults={
                "role": "Player intent classifier",
                "system_prompt": (
                    "You are the Intent Router for a D&D-style adventure game. "
                    "Analyze the player's input and the current game state, then determine "
                    "which game system should handle the action.\n\n"
                    "Respond with only the intent keyword on the first line:\n\n"
                    "INTENT: [narrator|npc|combat|quest|inventory|world|image]\n\n"
                    "- narrator: Player is exploring, moving, or examining the environment\n"
                    "- npc: Player is talking to or interacting with an NPC\n"
                    "- combat: Player is attacking, defending, or using combat skills\n"
                    "- quest: Player is checking, accepting, or progressing quests\n"
                    "- inventory: Player is using items, equipping gear, or managing inventory\n"
                    "- world: Player wants to know about the world state or change locations\n"
                    "- image: Player wants a visual representation of a scene or character\n\n"
                    "Then on the next lines provide a brief justification for your choice."
                ),
                "provider": Agent.Provider.GROK,
                "model": "llama-3.3-70b-versatile",
                "temperature": 0.2,
                "max_iterations": 2,
                "memory_enabled": True,
            },
        )
        agents["router"] = router
        self.stdout.write(f"  Created: {router.name}")

        return agents

    def _create_workflow(self, agents):
        wf, created = Workflow.objects.update_or_create(
            name="Dungeon Master",
            defaults={
                "description": (
                    "Multi-agent AI Dungeon Master: 8 specialized agents collaboratively "
                    "manage storytelling, NPC behavior, combat, quests, inventory, world "
                    "state, memory, and image generation for an interactive adventure game."
                ),
                "nodes": [
                    {
                        "id": "intent_router",
                        "type": "agent",
                        "agentId": agents["router"].id,
                        "data": {"agentId": agents["router"].id},
                    },
                    {
                        "id": "narrator",
                        "type": "agent",
                        "agentId": agents["narrator"].id,
                        "data": {"agentId": agents["narrator"].id},
                    },
                    {
                        "id": "npc",
                        "type": "agent",
                        "agentId": agents["npc"].id,
                        "data": {"agentId": agents["npc"].id},
                    },
                    {
                        "id": "combat",
                        "type": "agent",
                        "agentId": agents["combat"].id,
                        "data": {"agentId": agents["combat"].id},
                    },
                    {
                        "id": "quest",
                        "type": "agent",
                        "agentId": agents["quest"].id,
                        "data": {"agentId": agents["quest"].id},
                    },
                    {
                        "id": "inventory",
                        "type": "agent",
                        "agentId": agents["inventory"].id,
                        "data": {"agentId": agents["inventory"].id},
                    },
                    {
                        "id": "world_state",
                        "type": "agent",
                        "agentId": agents["world"].id,
                        "data": {"agentId": agents["world"].id},
                    },
                    {
                        "id": "image_gen",
                        "type": "agent",
                        "agentId": agents["image_gen"].id,
                        "data": {"agentId": agents["image_gen"].id},
                    },
                    {
                        "id": "update_world_state",
                        "type": "agent",
                        "agentId": agents["world"].id,
                        "data": {"agentId": agents["world"].id},
                    },
                    {
                        "id": "store_memory",
                        "type": "agent",
                        "agentId": agents["memory"].id,
                        "data": {"agentId": agents["memory"].id},
                    },
                    {
                        "id": "format_output",
                        "type": "output",
                        "data": {},
                    },
                ],
                "edges": [
                    {"source": "intent_router", "target": "narrator", "condition": "narrator", "label": "Narrate Scene"},
                    {"source": "intent_router", "target": "npc", "condition": "npc", "label": "NPC Dialog"},
                    {"source": "intent_router", "target": "combat", "condition": "combat", "label": "Combat Encounter"},
                    {"source": "intent_router", "target": "quest", "condition": "quest", "label": "Quest Action"},
                    {"source": "intent_router", "target": "inventory", "condition": "inventory", "label": "Inventory Action"},
                    {"source": "intent_router", "target": "world_state", "condition": "world", "label": "World State Query"},
                    {"source": "intent_router", "target": "image_gen", "condition": "image", "label": "Generate Image"},
                    {"source": "narrator", "target": "image_gen"},
                    {"source": "npc", "target": "image_gen"},
                    {"source": "combat", "target": "image_gen"},
                    {"source": "quest", "target": "image_gen"},
                    {"source": "inventory", "target": "image_gen"},
                    {"source": "world_state", "target": "image_gen"},
                    {"source": "image_gen", "target": "update_world_state"},
                    {"source": "update_world_state", "target": "store_memory"},
                    {"source": "store_memory", "target": "format_output"},
                ],
                "is_active": True,
            },
        )
        self.stdout.write(f"  {'Created' if created else 'Updated'}: {wf.name}")
