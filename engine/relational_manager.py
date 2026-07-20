# hari/engine/relational_manager.py
"""Per-session relational state management."""

from models.relational import RelationshipModel


class RelationalManager:
    """Manages RelationshipModel persistence and glacial drift."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.relationship = RelationshipModel(user_id=user_id)

    def apply_relational_decay(self) -> None:
        """
        Primitive 19: Relational forgetting.
        Very slow drift toward baseline (0.1 for familiarity, 0.5 for trust).
        """
        from engine.cognitive_params import FORGETTING

        rel = self.relationship
        df = FORGETTING.relationship_decay_factor

        rel.familiarity = rel.familiarity * df + (1.0 - df) * 0.1
        rel.trust_index = rel.trust_index * df + (1.0 - df) * 0.5
        rel.reciprocity_score = rel.reciprocity_score * df + (1.0 - df) * 0.5

        rel.familiarity = max(0.0, min(1.0, rel.familiarity))
        rel.trust_index = max(0.0, min(1.0, rel.trust_index))
        rel.reciprocity_score = max(0.0, min(1.0, rel.reciprocity_score))
