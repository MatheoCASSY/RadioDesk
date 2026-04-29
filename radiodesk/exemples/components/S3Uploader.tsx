"use client";
import React, { useState, useRef } from 'react';
import { completeLargeUpload, initLargeUpload, uploadPart } from '@/lib/multipartUpload';

type Props = {
  token: string;
  isProgrammateur: boolean;
  onUpload?: (ids: string[]) => void;
  onDiagnosticMessage?: (message: string) => void;
};

type FileWithMetadata = {
  file: File;
  title?: string;
  artist?: string;
  album?: string;
  year?: string;
  genre?: string;
  id?: string;
  status?: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
};

const MAX_UPLOAD_FILES = 25;
const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? 'https://nu8n9r0hl5.execute-api.eu-west-1.amazonaws.com').replace(/\/+$/, '');
const MULTIPART_CHUNK_SIZE_BYTES = 8 * 1024 * 1024;

function directApiUrl(path: string) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE}${normalizedPath}`;
}

function uploadEndpoints(path: string, preferProxyFirst = true) {
  const proxy = `/api${path.startsWith('/') ? path : `/${path}`}`;
  const direct = directApiUrl(path);
  return preferProxyFirst ? [proxy, direct] : [direct, proxy];
}

async function uploadFileMultipart(file: File, token: string): Promise<string> {
  const contentType = file.type || 'audio/mpeg';
  const uploadSession = await initLargeUpload(contentType, token);

  const parts: { ETag: string; PartNumber: number }[] = [];
  let partNumber = 1;

  for (let offset = 0; offset < file.size; offset += MULTIPART_CHUNK_SIZE_BYTES) {
    const chunk = file.slice(offset, offset + MULTIPART_CHUNK_SIZE_BYTES);
    const bytes = new Uint8Array(await chunk.arrayBuffer());
    const uploadedPart = await uploadPart(uploadSession, bytes, partNumber);
    parts.push(uploadedPart);
    partNumber += 1;
  }

  await completeLargeUpload(uploadSession, parts, token);
  return uploadSession.id;
}

// Extraction basique des métadonnées depuis le nom du fichier
// Format attendu: "Artist - Title.mp3" ou "Title.mp3"
function extractMetadataFromFilename(filename: string): Partial<FileWithMetadata> {
  const nameWithoutExt = filename.replace(/\.[^/.]+$/, '');
  
  // Essayer le format "Artist - Title"
  const match = nameWithoutExt.match(/^(.+?)\s*-\s*(.+)$/);
  if (match) {
    return {
      artist: match[1].trim(),
      title: match[2].trim(),
    };
  }
  
  // Sinon, utiliser juste le nom comme titre
  return { title: nameWithoutExt };
}

function normalizeId3Text(value: unknown): string {
  if (typeof value === 'string') return value.trim();
  if (typeof value === 'number') return String(value);
  return '';
}

type JsMediaTagSuccess = { tags?: Record<string, unknown> };
type JsMediaTagsReader = {
  read: (
    file: File | Blob | string,
    options: {
      onSuccess: (tag: JsMediaTagSuccess) => void;
      onError: (error: unknown) => void;
    }
  ) => void;
};

async function extractMetadataFromId3(file: File): Promise<Partial<FileWithMetadata>> {
  try {
    const mediaTagsModule = await import('jsmediatags/dist/jsmediatags.min.js');
    const moduleCandidate = mediaTagsModule as unknown as { default?: JsMediaTagsReader; read?: JsMediaTagsReader['read'] };
    const jsmediatags: JsMediaTagsReader | undefined = moduleCandidate.default
      ?? (typeof moduleCandidate.read === 'function' ? { read: moduleCandidate.read } : undefined);

    if (!jsmediatags || typeof jsmediatags.read !== 'function') {
      return {};
    }

    const tags = await new Promise<Record<string, unknown>>((resolve) => {
      jsmediatags.read(file, {
        onSuccess: (tag: { tags?: Record<string, unknown> }) => resolve(tag?.tags ?? {}),
        onError: () => resolve({}),
      });
    });

    const title = normalizeId3Text(tags.title);
    const artist = normalizeId3Text(tags.artist);
    const album = normalizeId3Text(tags.album);
    const year = normalizeId3Text(tags.year);

    let genre = normalizeId3Text(tags.genre);
    if (!genre) {
      const v1 = tags.TCON;
      if (Array.isArray(v1)) genre = normalizeId3Text(v1[0]);
      else genre = normalizeId3Text(v1);
    }

    return {
      title,
      artist,
      album,
      year,
      genre,
    };
  } catch {
    return {};
  }
}

export default function S3Uploader({ token, isProgrammateur, onUpload, onDiagnosticMessage }: Props) {
  const [files, setFiles] = useState<FileWithMetadata[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const remainingSlots = Math.max(0, MAX_UPLOAD_FILES - files.length);
  const finalizeUploadedFile = async (uploadedId: string, fileData: FileWithMetadata, index: number) => {
    setFiles(prev => {
      const updated = [...prev];
      updated[index] = { ...updated[index], status: 'success', id: uploadedId };
      return updated;
    });

    return uploadedId;
  };

  const addFiles = async (newFiles: File[]) => {
    const audioFiles = newFiles.filter(f => f.type.startsWith('audio/'));
    const remainingSlots = Math.max(0, MAX_UPLOAD_FILES - files.length);

    if (remainingSlots === 0) {
      onDiagnosticMessage?.(`Limite atteinte: vous ne pouvez pas ajouter plus de ${MAX_UPLOAD_FILES} fichiers.`);
      return;
    }

    const limitedAudioFiles = audioFiles.slice(0, remainingSlots);
    if (limitedAudioFiles.length < audioFiles.length) {
      onDiagnosticMessage?.(`Limite atteinte: seuls les ${MAX_UPLOAD_FILES} premiers fichiers seront pris en compte.`);
    }

    // Priorité aux tags ID3 quand disponibles; fallback sur le nom du fichier.
    const withMetadata = await Promise.all(limitedAudioFiles.map(async (file) => {
      const fromFilename = extractMetadataFromFilename(file.name);
      const fromId3 = await extractMetadataFromId3(file);
      return {
        file,
        title: fromId3.title || fromFilename.title || file.name.replace(/\.[^/.]+$/, ''),
        artist: fromId3.artist || fromFilename.artist || '',
        album: fromId3.album || fromFilename.album || '',
        year: fromId3.year || fromFilename.year || '',
        genre: fromId3.genre || fromFilename.genre || '',
        status: 'pending' as const,
      };
    }));

    setFiles(prev => [...prev, ...withMetadata].slice(0, MAX_UPLOAD_FILES));
  };

  const onFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      void addFiles(Array.from(e.target.files));
    }
  };

  const onDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(true);
  };

  const onDragLeave = () => {
    setDragOver(false);
  };

  const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files) {
      void addFiles(Array.from(e.dataTransfer.files));
    }
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const uploadFile = async (fileData: FileWithMetadata, index: number) => {
    if (!isProgrammateur) {
      const diagnostic = "Vous n'êtes pas programmateur";
      setFiles(prev => {
        const updated = [...prev];
        updated[index] = { ...updated[index], status: 'error', error: diagnostic };
        return updated;
      });
      onDiagnosticMessage?.(`Erreur upload ${fileData.file.name}: ${diagnostic}`);
      return null;
    }

    setFiles(prev => {
      const updated = [...prev];
      updated[index] = { ...updated[index], status: 'uploading' };
      return updated;
    });

    try {
      const uploadedId = await uploadFileMultipart(fileData.file, token);
      return await finalizeUploadedFile(uploadedId, fileData, index);
    } catch (e: unknown) {
      const errorMsg = (e as { message?: string })?.message ?? String(e);
      setFiles(prev => {
        const updated = [...prev];
        updated[index] = { ...updated[index], status: 'error', error: errorMsg };
        return updated;
      });
      onDiagnosticMessage?.(`Erreur upload ${fileData.file.name}: ${errorMsg}`);
      return null;
    }
  };

  const uploadAllFiles = async () => {
    if (!files.length) return;
    setUploading(true);

    const uploadedIds: string[] = [];
    for (let i = 0; i < files.length; i++) {
      const id = await uploadFile(files[i], i);
      if (id) uploadedIds.push(id);
    }

    setUploading(false);
    if (uploadedIds.length > 0) {
      setFiles([]);
      if (fileInputRef.current) fileInputRef.current.value = '';
      if (onUpload) onUpload(uploadedIds);
    }
  };

  const clearAll = () => {
    setFiles([]);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div style={{ padding: '1rem' }}>
      <div
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        style={{
          border: `2px dashed ${dragOver ? '#0099ff' : '#ccc'}`,
          borderRadius: '8px',
          padding: '2rem',
          textAlign: 'center',
          backgroundColor: dragOver ? '#f0f8ff' : 'transparent',
          cursor: 'pointer',
          transition: 'all 0.2s',
        }}
      >
        <label style={{ cursor: 'pointer', display: 'block' }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🎵</div>
          <div style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>
            Déposer des fichiers audio ici ou cliquer pour sélectionner
          </div>
          <div style={{ fontSize: '0.85rem', color: '#666' }}>
            Sélection multiple supportée · MP3, WAV, OGG, M4A · max {MAX_UPLOAD_FILES} fichiers
          </div>
          <div style={{ fontSize: '0.85rem', color: remainingSlots === 0 ? '#dc2626' : '#666', marginTop: '0.35rem' }}>
            {remainingSlots === 0
              ? `Limite atteinte: ${MAX_UPLOAD_FILES}/${MAX_UPLOAD_FILES} fichiers sélectionnés.`
              : `${files.length}/${MAX_UPLOAD_FILES} fichiers sélectionnés · ${remainingSlots} place${remainingSlots > 1 ? 's' : ''} restante${remainingSlots > 1 ? 's' : ''}.`}
          </div>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept="audio/*"
            onChange={onFileInputChange}
            style={{ display: 'none' }}
          />
        </label>
      </div>

      {files.length > 0 && (
        <div style={{ marginTop: '1.5rem' }}>
          <h3 style={{ marginBottom: '1rem' }}>{files.length} fichier(s) sélectionné(s) / {MAX_UPLOAD_FILES} max</h3>
          <div style={{ display: 'grid', gap: '1rem', maxHeight: '400px', overflowY: 'auto' }}>
            {files.map((fileData, index) => (
              <div
                key={index}
                style={{
                  border: '1px solid #ddd',
                  borderRadius: '6px',
                  padding: '1rem',
                  backgroundColor: fileData.status === 'success' ? '#f0fdf4' : fileData.status === 'error' ? '#fef2f2' : '#fff',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.7rem' }}>
                  <div>
                    <strong>{fileData.file.name}</strong>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    {fileData.status === 'uploading' && <span>⏳ Upload...</span>}
                    {fileData.status === 'success' && <span style={{ color: '#059669' }}>✅ Réussi</span>}
                    {fileData.status === 'error' && <span style={{ color: '#dc2626' }}>❌ Erreur</span>}
                  </div>
                </div>

                {fileData.error && (
                  <div style={{ color: '#dc2626', fontSize: '0.85rem', marginBottom: '0.5rem', whiteSpace: 'pre-line', wordBreak: 'break-word' }}>
                    {fileData.error}
                  </div>
                )}

                {fileData.status !== 'success' && (
                  <button
                    onClick={() => removeFile(index)}
                    disabled={fileData.status === 'uploading'}
                    style={{
                      padding: '0.4rem 0.8rem',
                      fontSize: '0.85rem',
                      borderRadius: '4px',
                      border: '1px solid #ddd',
                      backgroundColor: '#fff',
                      cursor: 'pointer',
                    }}
                  >
                    Retirer
                  </button>
                )}
              </div>
            ))}
          </div>

          <div style={{ marginTop: '1rem', display: 'flex', gap: '0.7rem' }}>
            <button
              onClick={() => void uploadAllFiles()}
              disabled={uploading || !files.some(f => f.status !== 'success')}
              style={{
                padding: '0.7rem 1.4rem',
                backgroundColor: uploading ? '#ccc' : '#000',
                color: '#fff',
                border: 'none',
                borderRadius: '6px',
                cursor: uploading ? 'not-allowed' : 'pointer',
                fontWeight: 'bold',
              }}
            >
              {uploading ? '⏳ Upload en cours...' : `Uploader ${files.filter(f => f.status !== 'success').length} fichier(s)`}
            </button>
            <button
              onClick={clearAll}
              disabled={uploading}
              style={{
                padding: '0.7rem 1.4rem',
                backgroundColor: '#f3f4f6',
                border: '1px solid #ddd',
                borderRadius: '6px',
                cursor: 'pointer',
              }}
            >
              Vider
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
