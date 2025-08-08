"use client";

import React, { useState } from "react";
import { FaStar } from "react-icons/fa";

interface VerbaButtonProps {
  title?: string;
  Icon?: typeof FaStar;
  onClick?: (...args: any[]) => void; // Updated to accept any number of arguments
  onMouseEnter?: (...args: any[]) => void;
  onMouseLeave?: (...args: any[]) => void;
  disabled?: boolean;
  key?: string;
  className?: string;
  type?: "button" | "submit" | "reset";
  selected?: boolean;
  selected_color?: string;
  selected_text_color?: string;
  circle?: boolean;
  text_class_name?: string;
  loading?: boolean;
  text_size?: string;
  icon_size?: number;
  onClickParams?: any[]; // New prop to pass additional parameters
  showTooltip?: boolean; // Whether to show custom tooltip for long text
}

const VerbaButton: React.FC<VerbaButtonProps> = ({
  title = "",
  key = "Button" + title,
  Icon,
  onClick = () => {},
  onMouseEnter = () => {},
  onMouseLeave = () => {},
  disabled = false,
  className = "",
  text_class_name = "",
  selected = false,
  selected_color = "bg-button-verba",
  selected_text_color = "text-text-verba-button",
  text_size = "text-xs",
  icon_size = 12,
  type = "button",
  loading = false,
  circle = false,
  onClickParams = [],
  showTooltip = false,
}) => {
  const [showCustomTooltip, setShowCustomTooltip] = useState(false);
  return (
    <div className="relative">
      <button
        type={type}
        key={key}
        className={
          className +
          ` p-3 transition-all active:scale-95 scale-100 duration-300 flex gap-1 items-center justify-center ${circle ? "rounded-full" : "rounded-lg"} hover:bg-button-hover-verba hover:text-text-verba-button ${selected ? selected_color + " shadow-md " + selected_text_color : " bg-button-verba text-text-alt-verba-button"} `
        }
        onClick={(e) => onClick(e, ...onClickParams)}
        disabled={disabled}
        onMouseEnter={(e) => {
          onMouseEnter(e);
          if (showTooltip && title && title.length > 20) {
            setShowCustomTooltip(true);
          }
        }}
        onMouseLeave={(e) => {
          onMouseLeave(e);
          setShowCustomTooltip(false);
        }}
      >
        {loading ? (
          <span className="text-text-verba-button loading loading-spinner loading-xs"></span>
        ) : (
          <>
            {Icon && <Icon size={icon_size} className="w-[20px]" />}
            {title && (
              <p title={showTooltip ? undefined : title} className={text_size + " " + text_class_name}>
                {title}
              </p>
            )}
          </>
        )}
      </button>

      {/* Custom Tooltip for long text */}
      {showTooltip && showCustomTooltip && title && title.length > 20 && (
        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 z-50 p-3 bg-bg-verba text-text-verba text-xs rounded-lg shadow-lg border border-gray-300 max-w-xs">
          <p className="whitespace-pre-wrap break-words">{title}</p>
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-bg-verba"></div>
        </div>
      )}
    </div>
  );
};

export default VerbaButton;
