# program.health.care_continuity.beast3.py
# Beast System 3.0 — Deterministic Care Continuity Engine

from dataclasses import dataclass, field
import time
import hashlib

# Scoring weights for continuity components
CONTINUITY_WEIGHTS = {
    "referrals": 0.25,
    "followups": 0.25,
    "provider_stability": 0.25,
    "appointment_adherence": 0.25
}

@dataclass
class CareContinuityPacket:
    family_id: str
    referrals: list
    followups: list
    provider_transitions: int
    missed_appointments: int
    continuity_score: float
    escalation_required: bool
    ts: float = field(default_factory=time.time)
    hash: str = ""

    def finalize(self):
        serialized = f"{self.family_id}{self.referrals}{self.followups}{self.provider_transitions}{self.missed_appointments}{self.continuity_score}{self.escalation_required}{self.ts}".encode("utf-8")
        self.hash = hashlib.sha256(serialized).hexdigest()

@dataclass
class CareContinuityProfile:
    family_id: str
    packets: list = field(default_factory=list)
    last_update: float = field(default_factory=time.time)

    def add_packet(self, packet: CareContinuityPacket):
        packet.finalize()
        self.packets.append(packet)
        self.last_update = packet.ts

class CareContinuityEngine:
    def __init__(self, kernel):
        self.kernel = kernel
        self.continuity_profiles = {}

    def create_profile(self, family_id: str):
        profile = CareContinuityProfile(family_id)
        self.continuity_profiles[family_id] = profile

        return self.kernel.dispatch(
            module="health.care_continuity",
            action="create_profile",
            payload={"family_id": family_id}
        )

    def submit_continuity(self, family_id: str, referrals: list, followups: list, provider_transitions: int, missed_appointments: int):
        if family_id not in self.continuity_profiles:
            raise ValueError("Continuity profile not found")

        # Compute continuity components
        referral_score = 1.0 if len(referrals) > 0 else 0.0
        followup_score = 1.0 if len(followups) > 0 else 0.0
        provider_stability = 1.0 if provider_transitions == 0 else max(0.0, 1.0 - (provider_transitions * 0.2))
        appointment_adherence = 1.0 if missed_appointments == 0 else max(0.0, 1.0 - (missed_appointments * 0.25))

        continuity_score = (
            referral_score * CONTINUITY_WEIGHTS["referrals"] +
            followup_score * CONTINUITY_WEIGHTS["followups"] +
            provider_stability * CONTINUITY_WEIGHTS["provider_stability"] +
            appointment_adherence * CONTINUITY_WEIGHTS["appointment_adherence"]
        )

        continuity_score = round(continuity_score, 4)

        # Escalation logic
        escalation_required = continuity_score < 0.40 or missed_appointments >= 3

        packet = CareContinuityPacket(
            family_id=family_id,
            referrals=referrals,
            followups=followups,
            provider_transitions=provider_transitions,
            missed_appointments=missed_appointments,
            continuity_score=continuity_score,
            escalation_required=escalation_required
        )

        profile = self.continuity_profiles[family_id]
        profile.add_packet(packet)

        return self.kernel.dispatch(
            module="health.care_continuity",
            action="submit_continuity",
            payload={
                "family_id": family_id,
                "referrals": referrals,
                "followups": followups,
                "provider_transitions": provider_transitions,
                "missed_appointments": missed_appointments,
                "continuity_score": continuity_score,
                "escalation_required": escalation_required
            }
        )

    def get_packets(self, family_id: str):
        return self.continuity_profiles.get(family_id, None)
