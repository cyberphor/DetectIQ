import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_openai import OpenAIEmbeddings

from detectiq.core.config import config
from detectiq.core.llm.sigma_rules import SigmaLLM
from detectiq.core.llm.snort_rules import SnortLLM
from detectiq.core.llm.yara_rules import YaraLLM
from detectiq.core.utils.logging import get_logger
from detectiq.core.utils.sigma.rule_updater import SigmaRuleUpdater
from detectiq.core.utils.snort.rule_updater import SnortRuleUpdater
from detectiq.core.utils.yara.rule_updater import YaraRuleUpdater
from detectiq.webapp.backend.rules.models import StoredRule
from detectiq.webapp.backend.services.rule_service import DjangoRuleRepository
from detectiq.webapp.backend.utils.mitre_utils import extract_mitre_info

logger = get_logger(__name__)


class RulesetManager:
    """Manages initialization and updates of rulesets and vector stores."""

    def __init__(self):
        """Initialize the ruleset manager."""
        logger.info("Initializing RulesetManager")
        self.rule_dirs = config.rule_directories
        self.vector_store_dirs = config.vector_store_directories
        self.rule_repository = DjangoRuleRepository()

        # Ensure directories exist and are Path objects
        for directory in [*self.rule_dirs.values(), *self.vector_store_dirs.values()]:
            if isinstance(directory, str):
                directory = Path(directory)
            directory.mkdir(parents=True, exist_ok=True)

        # Initialize rule updaters
        self.sigma_updater = SigmaRuleUpdater(rule_dir=str(self.rule_dirs["sigma"]))
        self.yara_updater = YaraRuleUpdater(rule_dir=str(self.rule_dirs["yara"]))
        self.snort_updater = SnortRuleUpdater(rule_dir=str(self.rule_dirs["snort"]))

        # Initialize LLM handlers without auto-update
        self.sigma_llm = SigmaLLM(
            rule_dir=str(self.rule_dirs["sigma"]),
            auto_update=False,
            vector_store_dir=str(self.vector_store_dirs["sigma"]),
            embedding_model=OpenAIEmbeddings(model="text-embedding-3-small"),
        )
        self.yara_llm = YaraLLM(
            rule_dir=str(self.rule_dirs["yara"]),
            auto_update=False,
            vector_store_dir=str(self.vector_store_dirs["yara"]),
            embedding_model=OpenAIEmbeddings(model="text-embedding-3-small"),
        )
        self.snort_llm = SnortLLM(
            rule_dir=str(self.rule_dirs["snort"]),
            auto_update=False,
            vector_store_dir=str(self.vector_store_dirs["snort"]),
            embedding_model=OpenAIEmbeddings(model="text-embedding-3-small"),
        )

        # Define source mapping as a class constant
        self.SOURCE_MAPPING = {"sigma": "SigmaHQ", "yara": "YARA-Forge", "snort": "Snort3 Community"}

    def _validate_severity(self, severity: str) -> str:
        """Validate and normalize severity value."""
        valid_severities = ["informational", "low", "medium", "high", "critical"]
        normalized = severity.lower()
        return normalized if normalized in valid_severities else "medium"

    async def _update_rules(self, rule_type: str) -> List[Dict[str, Any]]:
        """Update rules using appropriate updater and return loaded rules."""
        try:
            logger.info(f"Updating {rule_type} rules...")
            updater = {"sigma": self.sigma_updater, "yara": self.yara_updater, "snort": self.snort_updater}[rule_type]

            # First ensure the rule directory exists and is empty
            rule_dir = Path(self.rule_dirs[rule_type])
            if rule_dir.exists():
                logger.info(f"Cleaning {rule_type} rule directory")
                try:
                    # Remove directory and all its contents recursively
                    shutil.rmtree(rule_dir)
                    # Recreate empty directory
                    rule_dir.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Successfully cleaned {rule_type} rule directory")
                except Exception as e:
                    logger.error(f"Error cleaning {rule_type} rule directory: {e}")
                    raise

            # Now update the rules
            await updater.update_rules(force=True)

            # Load the rules
            rules = await updater.load_rules()
            logger.info(f"Successfully updated and loaded {len(rules)} {rule_type} rules")
            return rules

        except Exception as e:
            logger.error(f"Error updating {rule_type} rules: {str(e)}")
            raise

    async def _store_rules_in_db(self, rule_type: str, rules: List[Dict[str, Any]]) -> None:
        """Store rules in the database."""
        try:
            logger.info(f"Storing {len(rules)} {rule_type} rules in database")

            # Get the appropriate source for this rule type
            source = self.SOURCE_MAPPING.get(rule_type)
            if not source:
                raise ValueError(f"Unknown rule type: {rule_type}")

            # First, delete existing rules of this type and source
            logger.info(f"Deleting existing {rule_type} rules from {source}")
            await self.rule_repository.delete_rules_by_type_and_source(rule_type, source)
            logger.info(f"Successfully deleted existing {rule_type} rules from {source}")

            formatted_rules = []
            for i, rule in enumerate(rules):
                try:
                    # Debug log the raw rule
                    logger.debug(f"Processing rule {i}: {rule}")

                    # Validate rule structure
                    if not isinstance(rule, dict):
                        logger.error(f"Rule {i} is not a dictionary: {rule}")
                        continue

                    if "metadata" not in rule or "content" not in rule:
                        logger.error(f"Rule {i} missing required fields: {rule}")
                        continue

                    # Extract and validate severity
                    raw_severity = rule.get("severity") or rule["metadata"].get("severity", "medium")
                    validated_severity = self._validate_severity(raw_severity)

                    # Extract title based on rule type
                    title = self._extract_rule_title(rule_type, rule, i)

                    if title.lower().startswith("untitled"):
                        logger.warning(f"Untitled rule detected: {title}")

                    # Extract MITRE information
                    mitre_tactics, mitre_techniques = extract_mitre_info(rule_type, rule)

                    # Format rule data for database
                    formatted_rule = {
                        "title": title,
                        "content": str(rule.get("content", "")),
                        "type": rule_type,
                        "severity": validated_severity,
                        "enabled": True,
                        "description": rule["metadata"].get("description", ""),
                        "metadata": rule.get("metadata", {}),
                        "source": str(rule.get("metadata", {}).get("source")),
                        "package_type": str(rule.get("metadata", {}).get("package_type")),
                        "mitre_tactics": mitre_tactics,
                        "mitre_techniques": mitre_techniques,
                    }

                    # Debug log the formatted rule
                    logger.debug(f"Formatted rule {i}: {formatted_rule}")
                    formatted_rules.append(formatted_rule)

                except Exception as e:
                    logger.error(f"Error formatting rule {i}: {e}, rule data: {rule}")
                    continue

            if not formatted_rules:
                logger.warning(f"No valid rules to store for type {rule_type}")
                return

            # Store rules in database
            logger.info(f"Attempting to save {len(formatted_rules)} formatted rules")
            await self.rule_repository.bulk_save_rules(formatted_rules)
            logger.info(f"Successfully stored {len(formatted_rules)} {rule_type} rules in database")

        except Exception as e:
            logger.error(f"Error storing {rule_type} rules in database: {str(e)}")
            raise

    def _extract_rule_title(self, rule_type: str, rule: Dict[str, Any], index: int) -> str:
        """Extract title from rule based on rule type."""
        if rule_type == "snort":
            # For Snort rules, use the msg field as the title
            msg_match = re.search(r'msg:"([^"]+)";', rule["content"])
            return msg_match.group(1) if msg_match else f"Untitled_Snort_Rule_{index}"
        elif rule_type == "yara":
            # For YARA rules, try multiple fields
            return (
                rule["metadata"].get("rule_name")
                or rule["metadata"].get("title")
                or rule.get("title", f"Untitled_YARA_Rule_{index}")
            ).replace("_", " ")
        else:  # sigma
            # For Sigma rules, use the title field
            return rule["metadata"].get("title", f"Untitled_Sigma_Rule_{index}").replace("_", " ")

    async def _clear_database_rules(self, rule_type: Optional[str] = None) -> None:
        """Clear rules from database.

        Args:
            rule_type: Optional rule type to clear. If None, clears all rules.
        """
        try:
            if rule_type:
                logger.info(f"Clearing {rule_type} rules from database")
                await self.rule_repository.delete_rules_by_type(rule_type)
            else:
                logger.info("Clearing all rules from database")
                await self.rule_repository.delete_all_rules()

            logger.info("Successfully cleared rules from database")
        except Exception as e:
            logger.error(f"Error clearing rules from database: {str(e)}")
            raise

    async def initialize_rulesets(
        self, create_vectorstores: bool = False, rule_types: Optional[List[str]] = None
    ) -> None:
        """Initialize rulesets and optionally create vector stores.

        Args:
            create_vectorstores: Whether to create vector stores for the rules
            rule_types: List of rule types to initialize. If None, initializes all types.
        """
        try:
            # Determine which rule types to initialize
            types_to_init = rule_types if rule_types else ["sigma", "yara", "snort"]

            # Clear rules from database for types being initialized
            for rule_type in types_to_init:
                await self._clear_database_rules(rule_type)

            for rule_type in types_to_init:
                logger.info(f"Initializing {rule_type} ruleset")

                # First update and load the rules
                rules = await self._update_rules(rule_type)

                # Store rules in database
                await self._store_rules_in_db(rule_type, rules)

                # Create vector store if requested
                if create_vectorstores:
                    llm_handler = {"sigma": self.sigma_llm, "yara": self.yara_llm, "snort": self.snort_llm}[rule_type]

                    try:
                        await llm_handler.create_vectordb()
                        logger.info(f"Successfully created vector store for {rule_type}")
                    except Exception as e:
                        logger.error(f"Error creating vector store for {rule_type}: {e}")
                        continue

        except Exception as e:
            logger.error(f"Error during ruleset initialization: {str(e)}")
            raise
