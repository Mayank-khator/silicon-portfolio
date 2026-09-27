'use client';
import * as D from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
export function Dialog({open,onOpenChange,title,description,children}:{open:boolean;onOpenChange:(v:boolean)=>void;title:string;description?:string;children:React.ReactNode}) {return <D.Root open={open} onOpenChange={onOpenChange}><D.Portal><D.Overlay className="dialog-overlay"/><D.Content className="dialog-content"><div className="dialog-heading"><D.Title>{title}</D.Title><D.Close className="icon-button" aria-label="Close dialog"><X size={19}/></D.Close></div><D.Description className="muted">{description||'Review and update your portfolio workspace.'}</D.Description>{children}</D.Content></D.Portal></D.Root>}
