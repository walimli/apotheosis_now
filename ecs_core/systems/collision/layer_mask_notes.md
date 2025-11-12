**Short answer:**  
Use the **constant names** (like `LAYER_PLAYER`) when you create a `Collider`. The values are integers under the hood, but writing the names makes your code clear and safe.

```python
# Good – use the constant
collider = Collider(
    diameter=32,
    layer=LAYER_PLAYER,      # this entity is a player
    mask=LAYER_ENEMY | LAYER_WALL   # it collides with enemies and walls
)
```

---

### How layers work (plain English)

1. **Every collider has two numbers**  
   * `layer` – “what **I am**”  
   * `mask`  – “what **I care about**”

2. **Collision only happens when both sides agree**  
   * A checks: “Does B’s `layer` match anything in my `mask`?”  
   * B checks: “Does A’s `layer` match anything in my `mask`?”  
   If **both** say *yes*, they collide.

3. **Bit-masking trick**  
   The constants are powers of two (`1, 2, 4, 8…`) so you can combine them with `|` (OR):  
   ```python
   LAYER_ENEMY | LAYER_WALL   # = 2 | 8 = 10
   ```
   `&` (AND) tests overlap:  
   ```python
   if collider_a.mask & collider_b.layer:
       # they can collide
   ```

4. **Common setups**  
   | Entity   | `layer`          | `mask` (what it hits)               |
   |----------|------------------|-------------------------------------|
   | Player   | `LAYER_PLAYER`   | `LAYER_ENEMY \| LAYER_WALL`         |
   | Enemy    | `LAYER_ENEMY`    | `LAYER_PLAYER \| LAYER_PROJECTILE`  |
   | Bullet   | `LAYER_PROJECTILE`| `LAYER_ENEMY`                       |
   | Pickup   | `LAYER_PICKUP`   | `LAYER_PLAYER` (set `is_trigger=True`) |

That’s it—use the constant names, combine with `|`, and the system does the rest.