"""Validate the game RPG catalog and simulate deterministic campaign budgets."""
import argparse
import csv
import json
import random
import sys
from pathlib import Path

def threshold(level):
    return 50 * (level - 1) * (level + 2)

def validate(data):
    def require(condition, message):
        if not condition:
            raise ValueError(message)
    items = {i["id"]: i for i in data["items"]}
    require(len(items) == len(data["items"]), "duplicate item ID")
    require(data["schema"] == 1 and data["level_cap"] == 100, "schema/cap")
    require(all(i["price"] >= 0 and i["stack"] > 0 and 1 <= i["level"] <= 100 for i in items.values()), "item bounds")
    require([c["id"] for c in data["chapters"]] == list(range(1, 27)), "chapter coverage")
    last = 1
    for c in data["chapters"]:
        level = c["target_level"]
        require(last <= level <= 100 and c["xp_budget"] == threshold(level) - threshold(last), "XP curve")
        require(0 <= c["essential_spend"] <= c["gold_budget"], "budget")
        last = level
    require(last == 100, "final level")
    for r in data["recipes"]:
        require(r["output"] in items and r["gold"] >= 0 and r["count"] > 0 and bool(r["inputs"]), "recipe")
        require(all(k in items and v > 0 for k,v in r["inputs"].items()), "recipe input")
        proceeds = items[r["output"]]["price"] * 40 // 100 * r["count"]
        cost = r["gold"] + sum(items[k]["price"] * v for k,v in r["inputs"].items())
        require(proceeds <= cost, "buy-craft-sell arbitrage")
    for table in data["loot"]:
        require(bool(table["entries"]) and all(e["id"] in items and e["weight"] > 0 for e in table["entries"]), "loot")
    skills = {s["id"]:s for s in data["skills"]}
    require(len(skills) == len(data["skills"]), "duplicate skills")
    for s in skills.values():
        require(all(k in skills and skills[k]["level"] < s["level"] for k in s["requires"]), "skill dependency")
    return items

def simulate(data, factor=1.0):
    gold = xp = 0
    for c in data["chapters"]:
        xp += c["xp_budget"]
        gold += int(c["gold_budget"] * factor) - c["essential_spend"]
        yield {"chapter":c["id"],"level":c["target_level"],"xp":xp,"gold":gold}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("catalog", type=Path)
    p.add_argument("--income-factor", type=float, default=1.0)
    args = p.parse_args()
    if not 0 <= args.income_factor <= 10:
        p.error("income factor outside [0,10]")
    data = json.loads(args.catalog.read_text(encoding="utf-8"))
    validate(data)
    rows = list(simulate(data, args.income_factor))
    writer = csv.DictWriter(sys.stdout, fieldnames=rows[0])
    writer.writeheader()
    writer.writerows(rows)
    return int(any(r["gold"] < 0 for r in rows))
if __name__ == "__main__":
    raise SystemExit(main())
