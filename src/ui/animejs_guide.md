# Everything You Need to Know About `npm i animejs`

**Anime.js** is a lightweight, high-performance JavaScript animation engine with a simple yet powerful API. It allows you to animate CSS properties, SVG elements, DOM attributes, and JavaScript objects seamlessly.

---

## 1. Installation & Import

### Installation via NPM
```bash
npm install animejs
```

### Installation via alternative package managers:
```bash
yarn add animejs
# or
pnpm add animejs
```

### Imports

#### Anime.js v3 (Default / Classic):
```javascript
import anime from 'animejs/lib/anime.es.js';
// or
import anime from 'animejs';
```

#### Anime.js v4 (Latest / Modular):
```javascript
import { animate, createTimeline, stagger } from 'animejs';
```

---

## 2. Core Concepts & Target Types

Anime.js can target virtually anything in the DOM or JavaScript environment:

| Target Type | Example |
| :--- | :--- |
| **CSS Selector** | `targets: '.square'` or `targets: '#ball'` |
| **DOM Element(s)** | `targets: document.querySelector('.card')` |
| **NodeList / Array** | `targets: document.querySelectorAll('.item')` |
| **JavaScript Object** | `targets: myObject` (e.g., `{ count: 0 }`) |
| **Multiple Targets** | `targets: ['.box1', '.box2', element]` |

---

## 3. Anime.js v3 (Classic Engine API)

### A. Basic Animation Syntax
```javascript
import anime from 'animejs';

anime({
  targets: '.box',
  translateX: 250,
  rotate: '1turn',
  backgroundColor: '#FF375F',
  duration: 1000,
  easing: 'easeInOutQuad',
  loop: true,
  direction: 'alternate'
});
```

---

### B. Key Parameters Reference

#### Animation Control Parameters:
- `duration`: Animation duration in milliseconds (default: `1000`).
- `delay`: Delay before starting the animation in ms (default: `0`).
- `endDelay`: Delay after completion before restarting/completing (default: `0`).
- `easing`: Easing function name or custom Cubic Bézier (e.g., `'easeInOutQuad'`, `'spring(1, 80, 10, 0)'`, `'cubicBezier(.5, .05, 1, .5)'`).
- `direction`: `'normal'`, `'reverse'`, `'alternate'`.
- `loop`: `true`, `false`, or a specific number of iterations (e.g., `3`).
- `autoplay`: `true` or `false` (default: `true`).

#### Property-Specific Parameters:
Parameters can also be specified individually per property:
```javascript
anime({
  targets: '.card',
  translateX: {
    value: 250,
    duration: 800,
    easing: 'easeOutExpo'
  },
  opacity: {
    value: 1,
    duration: 400,
    easing: 'linear'
  }
});
```

---

### C. Staggering Effects (`anime.stagger`)

Staggering allows you to animate multiple elements with staggered delays or values.

```javascript
anime({
  targets: '.grid-item',
  translateX: 270,
  rotate: '1turn',
  delay: anime.stagger(100), // Adds 100ms delay per item (0ms, 100ms, 200ms...)
  easing: 'easeOutQuad'
});
```

#### Advanced Stagger Options:
```javascript
anime({
  targets: '.grid-item',
  scale: [0.1, 1],
  delay: anime.stagger(50, { start: 500, from: 'center', grid: [14, 5], axis: 'x' })
});
```
- `from`: `'first'`, `'last'`, `'center'`, or index integer.
- `grid`: `[columns, rows]` for grid-based staggering.
- `axis`: `'x'` or `'y'`.

---

### D. Timelines (`anime.timeline`)

Timelines let you chain multiple animations together with precision timing.

```javascript
const tl = anime.timeline({
  easing: 'easeOutExpo',
  duration: 750
});

tl.add({
  targets: '.header',
  translateY: [-50, 0],
  opacity: [0, 1]
})
.add({
  targets: '.sidebar',
  translateX: [-100, 0],
  opacity: [0, 1]
}, '-=400') // Starts 400ms before previous animation ends
.add({
  targets: '.main-content',
  scale: [0.9, 1],
  opacity: [0, 1]
}, '+=200'); // Starts 200ms after previous animation ends
```

---

### E. Playback Controls & Callbacks

```javascript
const animation = anime({
  targets: '.box',
  translateX: 250,
  autoplay: false,
  // Callbacks
  begin: (anim) => console.log('Started'),
  update: (anim) => console.log(`Progress: ${anim.progress}%`),
  complete: (anim) => console.log('Finished'),
  loopBegin: (anim) => console.log('Loop started'),
  loopComplete: (anim) => console.log('Loop ended')
});

// Control Methods
animation.play();
animation.pause();
animation.restart();
animation.reverse();
animation.seek(500); // Seek to 500ms
```

---

### F. SVG Animation Techniques

#### 1. SVG Line Drawing:
```javascript
anime({
  targets: 'path',
  strokeDashoffset: [anime.setDashoffset, 0],
  easing: 'easeInOutSine',
  duration: 1500,
  delay: (el, i) => i * 250,
  direction: 'alternate',
  loop: true
});
```

#### 2. Motion Path Following (`anime.path`):
```javascript
const path = anime.path('.motion-path path');

anime({
  targets: '.follower',
  translateX: path('x'),
  translateY: path('y'),
  rotate: path('angle'),
  easing: 'linear',
  duration: 2000,
  loop: true
});
```

#### 3. SVG Shape Morphing:
```javascript
anime({
  targets: '.polygon',
  points: [
    { value: '220,10 300,210 170,250' },
    { value: '220,10 300,170 140,250' },
    { value: '220,80 300,170 170,250' }
  ],
  easing: 'easeOutQuad',
  duration: 1200,
  loop: true
});
```

---

## 4. Anime.js v4 (Next-Gen Modular API)

In **Anime.js v4**, the architecture switched to named modular imports for smaller bundle sizes and tree-shaking support, along with native Web Animations API (WAAPI) integration.

### Key Syntax Differences (v3 vs v4):

| Feature | Anime.js v3 | Anime.js v4 |
| :--- | :--- | :--- |
| **Import** | `import anime from 'animejs'` | `import { animate, createTimeline } from 'animejs'` |
| **Execution** | `anime({ targets: '.box', ... })` | `animate('.box', { ... })` |
| **Easing Parameter** | `easing: 'outQuad'` | `ease: 'outQuad'` |
| **End Value Syntax** | `opacity: { value: 1 }` | `opacity: { to: 1 }` |
| **Direction** | `direction: 'alternate'` | `alternate: true` / `reversed: true` |

### v4 Example:
```javascript
import { animate, stagger } from 'animejs';

animate('.item', {
  x: 200,
  rotate: { from: 0, to: 360 },
  opacity: { to: 1, duration: 400 },
  delay: stagger(100),
  ease: 'inOutExpo',
  loop: true,
  alternate: true
});
```

---

## 5. Using Anime.js with React (Vite / Next.js)

When using Anime.js in React, always attach animations to `ref` handles and clean up on unmount.

```jsx
import React, { useEffect, useRef } from 'react';
import anime from 'animejs';

export default function AnimatedBox() {
  const boxRef = useRef(null);
  const animationRef = useRef(null);

  useEffect(() => {
    animationRef.current = anime({
      targets: boxRef.current,
      translateX: 250,
      rotate: '1turn',
      duration: 1000,
      easing: 'easeInOutQuad',
      autoplay: true
    });

    return () => {
      // Clean up animation on unmount
      if (animationRef.current) animationRef.current.pause();
    };
  }, []);

  return (
    <div
      ref={boxRef}
      style={{ width: 50, height: 50, background: '#6366f1', borderRadius: 8 }}
    />
  );
}
```

---

## 6. Performance Best Practices

1. **Use GPU-Accelerated Properties**: Animate `transform` (`translateX`, `translateY`, `scale`, `rotate`) and `opacity` rather than `top`, `left`, `width`, or `height` to prevent browser reflows/layout thrashing.
2. **Clean Up Timelines**: Always `.pause()` or cancel active animations when unmounting components in React, Vue, or Svelte.
3. **Use `anime.stagger()` for Lists**: Avoid running separate `anime()` calls in loops; pass array/selectors directly into target with `stagger()` for better performance.
