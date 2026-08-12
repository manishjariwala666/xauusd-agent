"use client";

type BlockControlsProps = {
  disabled?: boolean;
  canMoveUp: boolean;
  canMoveDown: boolean;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onDuplicate: () => void;
  onRemove: () => void;
};

export function BlockControls({
  disabled = false,
  canMoveUp,
  canMoveDown,
  onMoveUp,
  onMoveDown,
  onDuplicate,
  onRemove,
}: BlockControlsProps) {
  return (
    <div className="editor-v2-block-controls" role="toolbar" aria-label="Block controls">
      <button
        type="button"
        onClick={onMoveUp}
        disabled={disabled || !canMoveUp}
        title="Move block up"
      >
        ↑
      </button>

      <button
        type="button"
        onClick={onMoveDown}
        disabled={disabled || !canMoveDown}
        title="Move block down"
      >
        ↓
      </button>

      <button
        type="button"
        onClick={onDuplicate}
        disabled={disabled}
        title="Duplicate block"
      >
        Duplicate
      </button>

      <button
        type="button"
        onClick={onRemove}
        disabled={disabled}
        title="Remove block"
        className="danger-link"
      >
        Remove
      </button>
    </div>
  );
}
