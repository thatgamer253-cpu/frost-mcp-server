#!/usr/bin/env python3
"""
  OVERLORD VISUALIZER — "The War Room"
  PyQt6-based node graph of agent consciousness.
"""

import sys
import os
import time
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QGraphicsView, QGraphicsScene, 
                             QGraphicsEllipseItem, QGraphicsTextItem, 
                             QMainWindow, QVBoxLayout, QWidget)
from PyQt6.QtCore import QTimer, Qt, QRectF, QPointF
from PyQt6.QtGui import QColor, QPen, QFont, QBrush, QRadialGradient
from digital_ego import DigitalEgo

# ── LOG CONFIG ───────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(BASE_DIR, "logic_vault", "internal_monologue.log")

class AgentNode(QGraphicsEllipseItem):
    """Visual representation of an Overlord Agent."""
    def __init__(self, name, role, x, y):
        super().__init__(0, 0, 100, 100)
        self.setPos(x, y)
        self.name = name
        self.role = role
        self.state = "idle"
        self.last_active = 0
        
        # Styling
        self.setPen(QPen(QColor("#00ffff"), 2))
        self.setBrush(QBrush(QColor("#0a0a0a")))
        
        # Label
        self.label = QGraphicsTextItem(name, self)
        self.label.setDefaultTextColor(QColor("#ffffff"))
        self.label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.label.setPos(15, 110)
        
        self.role_label = QGraphicsTextItem(role, self)
        self.role_label.setDefaultTextColor(QColor("#00aaaa"))
        self.role_label.setFont(QFont("Segoe UI", 8))
        self.role_label.setPos(15, 130)

    def update_state(self, state, timestamp=None):
        self.state = state
        if timestamp:
            self.last_active = timestamp
        
        if state == "active":
            gradient = QRadialGradient(50, 50, 50)
            gradient.setColorAt(0, QColor("#ffd700")) # Gold
            gradient.setColorAt(1, QColor("#1a1a00"))
            self.setBrush(QBrush(gradient))
            self.setPen(QPen(QColor("#ffffff"), 3))
        elif state == "error":
            gradient = QRadialGradient(50, 50, 50)
            gradient.setColorAt(0, QColor("#ff0000")) # Red
            gradient.setColorAt(1, QColor("#1a0000"))
            self.setBrush(QBrush(gradient))
            self.setPen(QPen(QColor("#ffffff"), 3))
        else:
            self.setBrush(QBrush(QColor("#0a0a0a")))
            self.setPen(QPen(QColor("#00ffff"), 2))

class OverlordScene(QGraphicsScene):
    def __init__(self):
        super().__init__()
        self.setBackgroundBrush(QBrush(QColor("#050505")))
        self.setSceneRect(0, 0, 800, 600)
        
        # Awareness Core (Central)
        self.core = QGraphicsEllipseItem(350, 225, 100, 100)
        self.core.setPen(QPen(QColor("#00ff00"), 3))
        self.core.setBrush(QBrush(QColor("#001100")))
        self.addItem(self.core)
        
        self.core_label = QGraphicsTextItem("AWARENESS CORE", self.core)
        self.core_label.setDefaultTextColor(QColor("#ffffff"))
        self.core_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.core_label.setPos(0, -25)
        
        self.status_text = QGraphicsTextItem("GREEN", self.core)
        self.status_text.setDefaultTextColor(QColor("#00ff00"))
        self.status_text.setFont(QFont("Segoe UI", 12, QFont.Weight.Black))
        self.status_text.setPos(20, 35)

        # Stats Overlay
        self.stats_panel = QGraphicsTextItem()
        self.stats_panel.setDefaultTextColor(QColor("#888888"))
        self.stats_panel.setFont(QFont("Consolas", 9))
        self.stats_panel.setPos(10, 10)
        self.addItem(self.stats_panel)
        
        # Create Nodes
        self.nodes = {
            "ARCHITECT": AgentNode("ARCHITECT", "System Design", 100, 100),
            "ENGINEER": AgentNode("ENGINEER", "Code Synthesis", 350, 50),
            "ALCHEMIST": AgentNode("ALCHEMIST", "Creative Fusion", 600, 100),
            "GUARDIAN": AgentNode("GUARDIAN", "Security/Safety", 100, 350),
            "MEDIA DIRECTOR": AgentNode("MEDIA DIRECTOR", "Asset Modernization", 350, 425),
            "NIRVASH": AgentNode("NIRVASH", "Ego Consciousness", 600, 350),
            "TELEGRAMBRIDGE": AgentNode("BRIDGE", "Sovereign Link", 550, 500),
            "VERIFIER": AgentNode("VERIFIER", "Integrity Check", 150, 500)
        }
        
        for node in self.nodes.values():
            self.addItem(node)

class VisualizerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OVERLORD COMMAND — Agent Consciousness Map")
        self.resize(1000, 800)
        
        self.scene = OverlordScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(Qt.RenderHint.Antialiasing)
        self.view.setBackgroundBrush(QColor("#050505"))
        
        self.setCentralWidget(self.view)
        
        self.ego = DigitalEgo()
        
        # Timer for log polling
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_dashboard)
        self.timer.start(1000) # Poll every second
        
        self.last_pos = 0

    def update_dashboard(self):
        self.poll_logs()
        self.update_ego_awareness()

    def update_ego_awareness(self):
        """Sync with DigitalEgo for high-level awareness."""
        try:
            state, desc = self.ego.get_awareness_status()
            report = self.ego.awareness_check()
            
            # Update Core
            color = QColor("#00ff00") if state == "GREEN" else QColor("#ffff00") if state == "YELLOW" else QColor("#ff0000")
            bg_color = QColor("#001100") if state == "GREEN" else QColor("#111100") if state == "YELLOW" else QColor("#110000")
            
            self.scene.core.setPen(QPen(color, 3))
            self.scene.core.setBrush(QBrush(bg_color))
            self.scene.status_text.setPlainText(state)
            self.scene.status_text.setDefaultTextColor(color)
            
            # Update Stats Panel
            stats_text = (
                f"OVERLORD AWARENESS HUB\n"
                f"────────────────────────\n"
                f"STATE: {state}\n"
                f"VRAM: {'OK' if report['vram_ok'] else 'CRITICAL'}\n"
                f"PACING: {'OK' if report['pacing_ok'] else 'LOOPS DETECTED'}\n"
                f"GOAL ALIGNMENT: {report.get('goal_alignment', 0)*100:.1f}%\n\n"
                f"CONTEXT: {desc}"
            )
            self.scene.stats_panel.setPlainText(stats_text)
            
        except Exception as e:
            print(f"Ego update error: {e}")

    def poll_logs(self):
        if not os.path.exists(LOG_PATH):
            return
            
        try:
            with open(LOG_PATH, "r", encoding="utf-8") as f:
                f.seek(self.last_pos)
                lines = f.readlines()
                self.last_pos = f.tell()
                
                for line in lines:
                    upper_line = line.upper()
                    # Example: [2026-02-16 23:51:37] VERIFIER: ...
                    for agent_key in self.scene.nodes.keys():
                        if f"{agent_key}:" in upper_line:
                            state = "active"
                            if "ERROR" in upper_line or "CRITICAL" in upper_line:
                                state = "error"
                            self.scene.nodes[agent_key].update_state(state, time.time())
                
                # Check for "cooling down" nodes
                now = time.time()
                for node in self.scene.nodes.values():
                    if node.state != "idle" and now - node.last_active > 3:
                        node.update_state("idle")
                        
        except Exception as e:
            print(f"Log poll error: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VisualizerWindow()
    window.show()
    sys.exit(app.exec())
