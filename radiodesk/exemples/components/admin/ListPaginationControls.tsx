"use client";

import React from 'react';

export type PageSize = 10 | 25 | 50 | 100;

type ListPaginationControlsProps = {
  totalItems: number;
  currentPage: number;
  pageSize: PageSize;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: PageSize) => void;
  disabled?: boolean;
  itemLabel?: string;
};

export default function ListPaginationControls({
  totalItems,
  currentPage,
  pageSize,
  onPageChange,
  onPageSizeChange,
  disabled = false,
  itemLabel = 'elements',
}: ListPaginationControlsProps) {
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  const safePage = Math.max(0, Math.min(currentPage, totalPages - 1));
  const start = totalItems === 0 ? 0 : safePage * pageSize + 1;
  const end = Math.min(totalItems, (safePage + 1) * pageSize);

  return (
    <div className="fluff-pagination-controls">
      <label className="fluff-pagination-size">
        <span>Afficher</span>
        <select
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value) as PageSize)}
          disabled={disabled}
        >
          <option value={10}>10</option>
          <option value={25}>25</option>
          <option value={50}>50</option>
          <option value={100}>100</option>
        </select>
      </label>

      <div className="fluff-pagination-meta">
        Page {safePage + 1} / {totalPages} - {start}-{end} sur {totalItems} {itemLabel}
      </div>

      <div className="fluff-pagination-actions">
        <button
          type="button"
          onClick={() => onPageChange(Math.max(0, safePage - 1))}
          disabled={disabled || safePage <= 0}
        >
          Precedent
        </button>
        <button
          type="button"
          onClick={() => onPageChange(Math.min(totalPages - 1, safePage + 1))}
          disabled={disabled || safePage >= totalPages - 1}
        >
          Suivant
        </button>
      </div>
    </div>
  );
}
