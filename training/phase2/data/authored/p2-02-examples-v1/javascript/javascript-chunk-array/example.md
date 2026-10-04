# Plex P2 example draft-js-chunk-array

## Request

Write chunkArray(items, size). Return consecutive arrays of at most size items; preserve order and return an empty array if items is not an array or size is not a positive integer.

## Solution

```javascript
function chunkArray(items, size) {
  if (!Array.isArray(items) || !Number.isInteger(size) || size <= 0) {
    return [];
  }

  const chunks = [];
  for (let index = 0; index < items.length; index += size) {
    chunks.push(items.slice(index, index + size));
  }
  return chunks;
}
```
