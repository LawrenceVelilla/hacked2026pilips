# Extension Logic

## Flow

1. User hovers on a Pinterest pin image and sees a "Try on" pill button.
2. Clicking "Try on" adds that image URL to the garment list and opens the movable panel.
3. On a pin detail page, a "Try on" button is injected next to the Save button.
4. The panel calls the backend `/try-on` endpoint with the selected garment image URL.
5. The backend returns a try-on image URL which is shown in the panel.

## Notes

- The panel is injected into the Pinterest page and can be dragged or resized.
- Set the backend URL from the extension popup.
