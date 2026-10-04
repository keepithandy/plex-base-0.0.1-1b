# Plex P2 example draft-js-format-duration

## Request

Write formatDuration(seconds). For a finite nonnegative number, return whole elapsed minutes and remaining seconds as m:ss. Floor partial seconds. Return 0:00 for negative or non-finite input.

## Solution

```javascript
function formatDuration(seconds) {
  if (!Number.isFinite(seconds) || seconds < 0) {
    return "0:00";
  }

  const totalSeconds = Math.floor(seconds);
  const minutes = Math.floor(totalSeconds / 60);
  const remainingSeconds = String(totalSeconds % 60).padStart(2, "0");
  return `${minutes}:${remainingSeconds}`;
}
```
