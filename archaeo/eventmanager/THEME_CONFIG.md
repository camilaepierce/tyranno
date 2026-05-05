# REX Events Theme Configuration

This document explains how to customize the REX Events Management site's appearance through the centralized theme configuration system.

## Overview

All theme colors, typography, spacing, and styling are centralized in a single CSS file that uses CSS custom properties (variables), making it easy to change the appearance site-wide without modifying individual template files.

## Theme File Location

**File:** `/eventmanager/static/css/theme.css`

This is the only file you need to modify to change the entire site's appearance.

## CSS Custom Properties (Variables)

The theme system uses CSS custom properties (CSS variables) defined in the `:root` selector. These variables can be easily modified to change colors throughout the site.

### Primary Colors

```css
--primary-color: #2c3e50;        /* Main brand color (dark blue-gray) */
--secondary-color: #3498db;      /* Action/button color (bright blue) */
--accent-color: #e74c3c;         /* Accent color (red) */
```

### Status Colors

```css
--status-pending: #f39c12;       /* Pending approval (orange) */
--status-approved: #27ae60;      /* Approved status (green) */
--status-denied: #e74c3c;        /* Denied status (red) */
--status-flagged: #9b59b6;       /* Flagged status (purple) */
```

### Sidebar Colors

```css
--sidebar-bg: #2c3e50;           /* Sidebar background */
--sidebar-text: #ecf0f1;         /* Sidebar text color */
--sidebar-hover: #34495e;        /* Sidebar hover background */
--sidebar-active: #3498db;       /* Active sidebar item background */
```

### Neutral Colors

```css
--light-bg: #ecf0f1;             /* Light background (pages) */
--dark-bg: #2c3e50;              /* Dark background */
--border-color: #bdc3c7;         /* Border color */
--text-primary: #2c3e50;         /* Main text color */
--text-secondary: #7f8c8d;       /* Secondary text color */
--white: #ffffff;                /* White */
```

## How to Customize the Theme

### Step 1: Open the Theme File

Open `/eventmanager/static/css/theme.css` in your editor.

### Step 2: Locate the `:root` Section

Find the `:root` selector at the top of the file (around line 1-40).

### Step 3: Modify Variables

Change any variable value to your desired color. For example:

**Original:**
```css
--primary-color: #2c3e50;
```

**Modified:**
```css
--primary-color: #1a5490;  /* New blue shade */
```

### Step 4: Save and Reload

Save the file. The changes will take effect immediately when you reload the page in your browser.

## Common Customization Examples

### Change the Main Color Scheme

To change from blue to a green theme:

```css
:root {
  --primary-color: #27ae60;       /* Green */
  --secondary-color: #2ecc71;     /* Light green */
  --accent-color: #e74c3c;        /* Keep red for errors */
  /* ... other colors ... */
}
```

### Change Sidebar Appearance

```css
:root {
  --sidebar-bg: #1a1a1a;          /* Darker sidebar */
  --sidebar-text: #ffffff;
  --sidebar-hover: #333333;
  --sidebar-active: #4CAF50;      /* Green active state */
  /* ... other colors ... */
}
```

### Change Status Badge Colors

```css
:root {
  --status-pending: #FF9800;      /* Orange */
  --status-approved: #4CAF50;     /* Green */
  --status-denied: #F44336;       /* Red */
  --status-flagged: #2196F3;      /* Blue */
  /* ... other colors ... */
}
```

## Spacing and Typography

You can also customize spacing and typography by modifying these variables:

```css
/* Spacing */
--spacing-xs: 0.25rem;
--spacing-sm: 0.5rem;
--spacing-md: 1rem;
--spacing-lg: 1.5rem;
--spacing-xl: 2rem;

/* Typography */
--font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
--font-size-base: 14px;
--font-size-sm: 12px;
--font-size-lg: 16px;
--font-size-xl: 20px;
--font-size-2xl: 28px;

/* Border Radius */
--border-radius-sm: 4px;
--border-radius-md: 8px;
--border-radius-lg: 12px;
```

## Component Styles

The theme.css file includes predefined styles for common components:

- **Buttons** (`.btn`, `.btn-primary`, `.btn-success`, `.btn-danger`, `.btn-warning`)
- **Cards** (`.card`, `.card-header`, `.card-body`, `.card-footer`)
- **Status Badges** (`.status-badge`, `.status-pending`, `.status-approved`, etc.)
- **Forms** (inputs, textareas, labels, error lists)
- **Tables** (`.table` class)
- **Utility Classes** (spacing, text alignment, flexbox helpers)

## Browser Support

The theme system uses modern CSS features (CSS custom properties) that are supported in all modern browsers:
- Chrome/Edge 49+
- Firefox 31+
- Safari 9.1+
- Opera 36+

## Tips and Best Practices

1. **Use Hex Colors**: Hex color codes (#RRGGBB) work best in CSS variables
2. **Test Changes**: Always test your color changes across different browsers
3. **Maintain Contrast**: Ensure good color contrast for accessibility
4. **Document Changes**: Add comments to note why you made specific customizations
5. **Create Variants**: You can create multiple theme variants by duplicating and modifying the CSS file

## Advanced: Creating Theme Variants

To create multiple theme variants (e.g., light/dark mode), you can:

1. Create separate CSS files for each theme
2. Use CSS media queries for automatic light/dark mode detection
3. Use JavaScript to switch themes dynamically

Example of dark mode detection:
```css
@media (prefers-color-scheme: dark) {
  :root {
    --primary-color: #ecf0f1;
    --text-primary: #2c3e50;
    /* ... more dark mode colors ... */
  }
}
```

## Files That Use the Theme

All template files extend `base.html` and automatically inherit the theme through the linked theme.css:

- `/eventmanager/templates/base.html` - Main layout template
- `/eventmanager/templates/eventmanager/index.html` - Home page
- `/eventmanager/templates/eventmanager/detail.html` - Event details
- `/eventmanager/templates/eventmanager/create_event.html` - Create event form
- `/eventmanager/templates/eventmanager/myevents.html` - User's events
- `/eventmanager/templates/eventmanager/allevents.html` - All events (admin)
- `/eventmanager/templates/departments/*/pending.html` - Department approval pages

## Troubleshooting

**Changes not showing up?**
- Clear your browser cache (Ctrl+Shift+Delete or Cmd+Shift+Delete)
- Do a hard refresh (Ctrl+Shift+R or Cmd+Shift+R)
- Check that you saved the theme.css file

**Colors look wrong?**
- Ensure you're using valid hex color codes
- Check for typos in variable names
- Verify that you modified the `:root` section, not a specific selector

**Some elements not changing color?**
- Some elements might have inline styles that override the theme
- Check if there are component-specific overrides in the CSS file
- Increase CSS specificity if needed

## Support

For questions or issues with the theme system, refer to the main project documentation or contact the development team.
