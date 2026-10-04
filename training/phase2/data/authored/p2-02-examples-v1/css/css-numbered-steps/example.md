# Plex P2 example draft-css-numbered-steps

## Request

Number each list item in .steps with a CSS counter before its content, followed by a period and a half-rem gap.

## Solution

```css
.steps {
  counter-reset: steps;
  list-style: none;
  padding: 0;
}

.steps li::before {
  counter-increment: steps;
  content: counter(steps) ".";
  margin-inline-end: 0.5rem;
}
```
