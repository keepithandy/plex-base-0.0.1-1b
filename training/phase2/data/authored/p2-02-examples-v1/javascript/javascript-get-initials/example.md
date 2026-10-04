# Plex P2 example draft-js-get-initials

## Request

Write getInitials(name). Return the uppercase first character of each whitespace-separated name part, ignoring leading, trailing, and repeated spaces. Return an empty string for non-string or blank input.

## Solution

```javascript
function getInitials(name) {
  if (typeof name !== "string") {
    return "";
  }

  const parts = name.trim().split(/\s+/).filter(Boolean);
  return parts.map((part) => part[0].toUpperCase()).join("");
}
```
