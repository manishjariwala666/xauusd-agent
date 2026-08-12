import StarterKit from "@tiptap/starter-kit";
import Link from "@tiptap/extension-link";
import Image from "@tiptap/extension-image";
import Placeholder from "@tiptap/extension-placeholder";
import TextAlign from "@tiptap/extension-text-align";
import { Table } from "@tiptap/extension-table";
import TableRow from "@tiptap/extension-table-row";
import TableHeader from "@tiptap/extension-table-header";
import TableCell from "@tiptap/extension-table-cell";


const CmsLink = Link.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      underline: {
        default: true,
        parseHTML: element =>
          element.getAttribute("data-underline") !== "false",
        renderHTML: attributes =>
          attributes.underline === false
            ? {
                "data-underline": "false",
                class: "cms-link-no-underline",
              }
            : {
                "data-underline": "true",
              },
      },
      title: {
        default: null,
        parseHTML: element => element.getAttribute("title"),
        renderHTML: attributes =>
          attributes.title
            ? { title: attributes.title }
            : {},
      },
      ariaLabel: {
        default: null,
        parseHTML: element =>
          element.getAttribute("aria-label"),
        renderHTML: attributes =>
          attributes.ariaLabel
            ? { "aria-label": attributes.ariaLabel }
            : {},
      },
    };
  },
});

export function createEditorV2Extensions(placeholder: string) {
  return [
    StarterKit.configure({
      heading: {
        levels: [1, 2, 3, 4, 5, 6],
      },
      link: false,
    }),
    CmsLink.configure({
      openOnClick: false,
      autolink: true,
      defaultProtocol: "https",
    }),
    Image.configure({
      allowBase64: false,
      inline: false,
      HTMLAttributes: {
        loading: "lazy",
        decoding: "async",
      },
    }),
    Placeholder.configure({
      placeholder,
    }),
    TextAlign.configure({
      types: ["heading", "paragraph"],
      alignments: ["left", "center", "right", "justify"],
    }),
    Table.configure({
      resizable: true,
      allowTableNodeSelection: true,
    }),
    TableRow,
    TableHeader,
    TableCell,
  ];
}
