# Continuity Ledger

- Goal: Add win celebration animations and round-by-round score history to the Remi Game.
- Constraints/Assumptions:
  - Using existing Jinja2 templates (`remi_game.html`).
  - Need to handle score history in the backend or session.
  - UI should look premium/gaul as per previous conversations.
- Key decisions:
  - Use a library like `canvas-confetti` or similar for the celebration animation if possible, or vanilla CSS/JS.
  - Modify `Game` model or the data structure passed to the template to include a list of round scores.
- State:
  - Done: 
    - Added `RemiRound` model to `models.py`.
    - Updated `main.py` to save and fetch round history.
    - Updated `remi_game.html` with win animations (confetti) and history table.
    - Verified database table creation.
  - Now: Ready for user verification.
  - Next: Any further UI polish or feature requests.
- Open questions (UNCONFIRMED):
  - None at the moment.

- Working set:
  - `templates/remi_game.html`
  - `main.py`
  - `models.py`
