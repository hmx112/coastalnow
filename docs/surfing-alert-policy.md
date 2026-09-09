# Surfing active-alert policy

For Surfing, any NWS alert that is active for the location at the evaluated time suppresses the numerical Surf Conditions Score for that time.

- Active alert: `NOT RECOMMENDED`, no numerical score, no Best Surf Planning Window, not ranking-eligible.
- Future alert: does not affect scoring before its onset.
- Expired alert: no longer suppresses scoring after its end time.
- Official NWS alert details remain visible and take priority over CoastalNow planning metrics.

This conservative rule prevents alert-type gaps where a newly encountered NWS advisory or statement could remain visible while CoastalNow still presents a positive numerical Surf score.
