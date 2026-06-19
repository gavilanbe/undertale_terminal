"""Data-driven battle protocol helpers.

This module keeps the non-violent battle logic out of the rendering and
bullet code. A monster's protocol is a small state machine: complete the
current ACT step, survive any required proof, then use ^C to let the
process exit cleanly.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProtocolResult:
    """Outcome returned by a protocol action."""

    text: str
    advanced: bool = False
    spare_ready: bool = False
    survival_pending: bool = False


class ProtocolEngine:
    """Tracks a monster's ACT protocol as an explicit state machine."""

    def __init__(self, monster):
        self.monster = monster
        self.steps = list(monster.get("spare_steps", {}).get("sequence", []))
        self.min_turn = monster.get("spare_steps", {}).get("min_turn", 0)
        self.null_survival = bool(monster.get("null_survival"))
        self.progress = [0 for _ in self.steps]
        self.can_spare = (
            not self.steps and monster.get("spare_condition") is None
        )
        self.pending_survival = False

    def progress_dict(self):
        """Return progress in the legacy combat.py key format."""
        return {
            self._key(i, name): count
            for i, ((name, _required), count) in enumerate(
                zip(self.steps, self.progress))
            if count
        }

    def count_for(self, act_name):
        total = 0
        for (name, _required), count in zip(self.steps, self.progress):
            if name == act_name:
                total += count
        return total

    def route_line(self):
        """Return a concise, player-facing pacifist route."""
        route = self.monster.get("protocol_route")
        if route:
            return route

        if not self.steps:
            return "^C available"

        parts = []
        for step_name, required in self.steps:
            label = self._label(step_name).title()
            suffix = f" x{required}" if required > 1 else ""
            parts.append(f"{label}{suffix}")
        if self.null_survival:
            parts.append("Endure")
        parts.append("^C")
        return " -> ".join(parts)

    def next_action_line(self, turn):
        """Return the next concrete thing the player should try."""
        if self.can_spare:
            return "NEXT: ^C is ready."
        if self.pending_survival:
            return "NEXT: survive one attack hitless."
        if not self.steps:
            return "NEXT: ^C is available."

        current = self.current_index()
        if current is None:
            if turn < self.min_turn:
                return f"NEXT: endure {self.min_turn - turn} more turn(s)."
            return "NEXT: finish the turn cleanly."

        step_name, required = self.steps[current]
        done = min(required, self.progress[current])
        label = self._label(step_name).title()
        return f"NEXT: ACT {label} ({done + 1}/{required})."

    def current_step_name(self):
        """Return the current ACT command name, or None if none is pending."""
        if self.can_spare or self.pending_survival:
            return None
        current = self.current_index()
        if current is None:
            return None
        return self.steps[current][0]

    def progress_lines(self, turn):
        if self.can_spare:
            return ["OK MERCY ROUTE", "Use ^C to let it exit cleanly."]
        if self.pending_survival:
            return ["OK ACKNOWLEDGE 1/1", "> ENDURE 0/1 no hits"]
        if not self.steps:
            return ["No repair protocol.", "^C is already available."]

        lines = []
        current = self.current_index()
        hints = self.monster.get("protocol_step_hints", {})
        for i, (step_name, required) in enumerate(self.steps):
            done = min(required, self.progress[i])
            label = self._label(step_name).upper()
            if done >= required:
                prefix = "OK"
            elif i == current:
                prefix = ">"
            else:
                prefix = " "
            line = f"{prefix} {label} {done}/{required}"
            hint = hints.get(step_name)
            if hint and i == current and done < required:
                line = f"{line} {hint}"
            lines.append(line)

        if self.all_done() and turn < self.min_turn:
            lines.append(f"Hold {self.min_turn - turn} more turn(s) of proof.")
        return lines[:4]

    def use_act(self, act_name, turn):
        act_name = act_name.lower()

        if not self.steps:
            text = self.monster.get(f"{act_name}_text", f"* You tried {act_name}.")
            if self.monster.get("spare_condition") == act_name:
                self.can_spare = True
            return ProtocolResult(text, spare_ready=self.can_spare)

        current = self.current_index()
        if current is None:
            return self._handle_completed_protocol(act_name, turn)

        current_name, required = self.steps[current]
        if act_name != current_name:
            locked_key = f"{act_name}_locked_text"
            text = self.monster.get(
                locked_key,
                f"* {act_name.title()} does not fit\n"
                "  the current protocol step.",
            )
            return ProtocolResult(text)

        self.progress[current] = min(required, self.progress[current] + 1)
        count = self.progress[current]
        text_key = f"{act_name}_text_{count}"
        text = self.monster.get(
            text_key,
            self.monster.get(f"{act_name}_text", f"* You tried {act_name}."),
        )

        spare_ready = False
        survival_pending = False
        if self.all_done():
            if turn >= self.min_turn:
                if self.null_survival:
                    self.pending_survival = True
                    survival_pending = True
                else:
                    self.can_spare = True
                    spare_ready = True
            else:
                text += (
                    "\n\n* The protocol is correct,\n"
                    "  but it still needs proof\n"
                    "  under pressure."
                )

        return ProtocolResult(
            text,
            advanced=True,
            spare_ready=spare_ready,
            survival_pending=survival_pending,
        )

    def on_turn_end(self, turn, hitless):
        """Resolve proof that happens during the enemy attack."""
        if self.pending_survival:
            self.pending_survival = False
            if hitless:
                self.can_spare = True
                return ProtocolResult(
                    "* You didn't flinch.\n"
                    "  Null acknowledges you\n"
                    "  in return.\n"
                    "  (^C is now available)",
                    spare_ready=True,
                )
            return ProtocolResult(
                "* Null felt the flinch.\n"
                "  Acknowledge it again,\n"
                "  then endure the sink."
            )

        if self.all_done() and not self.can_spare and turn >= self.min_turn:
            self.can_spare = True
            return ProtocolResult(
                "* The proof holds.\n"
                "  The process table accepts\n"
                "  your intent.\n"
                "  (^C is now available)",
                spare_ready=True,
            )

        return None

    def current_index(self):
        for i, (_name, required) in enumerate(self.steps):
            if self.progress[i] < required:
                return i
        return None

    def all_done(self):
        return bool(self.steps) and self.current_index() is None

    def _handle_completed_protocol(self, act_name, turn):
        if self.null_survival and not self.can_spare and not self.pending_survival:
            self.pending_survival = True
            text = self.monster.get(
                f"{act_name}_text",
                "* You acknowledge the void again.",
            )
            return ProtocolResult(text, survival_pending=True)

        if not self.can_spare and turn >= self.min_turn:
            self.can_spare = True

        text = self.monster.get(f"{act_name}_text", f"* You tried {act_name}.")
        return ProtocolResult(text, spare_ready=self.can_spare)

    def _label(self, step_name):
        labels = self.monster.get("act_labels", {})
        return labels.get(step_name, step_name)

    @staticmethod
    def _key(index, step_name):
        return f"{index}:{step_name}"
