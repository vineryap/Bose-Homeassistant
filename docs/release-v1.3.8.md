## Fixed
- Corrected the Audio Mode/Dialogue Mode setter to use the Bose Music `PUT` request.
- Preserved Audio Mode options when the soundbar sends a partial status update.
- Rejected unavailable or unsupported Audio Mode selections and reported rejected changes.
- Added the missing CEC Option 7 display label.

## Notes
- Audio Mode supports only the modes advertised by your soundbar; options vary by model.
- This is an experimental fork. Back up Home Assistant before updating.
