declare module 'jsmediatags' {
  interface ID3Tag {
    tags: Record<string, unknown>;
  }

  interface JSMediaTags {
    read(
      file: File | Blob | string,
      options: {
        onSuccess: (tag: ID3Tag) => void;
        onError: (error: Error) => void;
      }
    ): void;
  }

  const jsmediatags: JSMediaTags;
  export = jsmediatags;
}

declare module 'jsmediatags/dist/jsmediatags.min.js' {
  interface ID3Tag {
    tags: Record<string, unknown>;
  }

  interface JSMediaTags {
    read(
      file: File | Blob | string,
      options: {
        onSuccess: (tag: ID3Tag) => void;
        onError: (error: Error) => void;
      }
    ): void;
  }

  const jsmediatags: JSMediaTags;
  export = jsmediatags;
}
