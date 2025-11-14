# Inventory Service Notes

## Equipped-slot notifications

`Inventory` already exposes the full slot list plus a general `on_change` hook, but systems that only care about the currently equipped (selected) slot can now subscribe to a dedicated selection-change signal. Every time the selected index moves or the selected slot’s contents/quantity change, the inventory emits the latest payload via any registered listeners.

```python
from services.inventory import Inventory

def handle_equip_change(slot_index: int, item_id: str | None, qty: int) -> None:
    if item_id == "pick_wooden_medallion":
        enable_pick_actions()
    else:
        disable_pick_actions()

player_inventory: Inventory = get_player_inventory()
player_inventory.add_selection_listener(handle_equip_change)

# Later, when the system is torn down:
player_inventory.remove_selection_listener(handle_equip_change)
```

**Listener contract**

- Callback signature: `(slot_index: int, item_id: Optional[str], qty: int)`
- Called synchronously inside the inventory, so keep handlers lightweight and exception-safe.
- Notifications fire whenever the hotbar selection changes **or** the selected slot’s contents/quantity change (e.g., stack increased/decreased) to keep downstream systems in sync.

Use this hook as the single source of truth for “equipped item” state; avoid duplicating flags in other services. Future gameplay systems can subscribe during their own bootstrap and unsubscribe on teardown to stay aligned with the inventory lifecycle.
