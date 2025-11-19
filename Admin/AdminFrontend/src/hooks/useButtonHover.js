import { useCallback } from 'react';

/**
 * Custom hook for handling button hover effects with consistent styling
 * @param {Object} colors - Color configuration object
 * @param {string} colors.normal.background - Normal state background color
 * @param {string} colors.normal.color - Normal state text color
 * @param {string} colors.normal.borderColor - Normal state border color
 * @param {string} colors.normal.boxShadow - Normal state box shadow
 * @param {string} colors.hover.background - Hover state background (gradient)
 * @param {string} colors.hover.color - Hover state text color
 * @param {string} colors.hover.borderColor - Hover state border color
 * @param {string} colors.hover.boxShadow - Hover state box shadow
 * @returns {Object} Object containing onMouseEnter and onMouseLeave handlers
 */
export const useButtonHover = (colors) => {
  const handleMouseEnter = useCallback((e) => {
    const target = e.target;
    target.style.background = colors.hover.background;
    target.style.color = colors.hover.color;
    target.style.boxShadow = colors.hover.boxShadow;
    target.style.borderColor = colors.hover.borderColor;
  }, [colors.hover]);

  const handleMouseLeave = useCallback((e) => {
    const target = e.target;
    target.style.background = colors.normal.background;
    target.style.color = colors.normal.color;
    target.style.boxShadow = colors.normal.boxShadow;
    target.style.borderColor = colors.normal.borderColor;
  }, [colors.normal]);

  return {
    onMouseEnter: handleMouseEnter,
    onMouseLeave: handleMouseLeave
  };
};
