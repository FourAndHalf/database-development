import { Component, ElementRef, ViewChild, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import html2canvas from 'html2canvas';
import { ToastService } from '../../services/toast.service';

@Component({
  selector: 'app-bug-report',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './bug-report.component.html',
  styleUrl: './bug-report.component.css'
})
export class BugReportComponent {
  private readonly http = inject(HttpClient);
  private readonly toast = inject(ToastService);

  isOpen = signal(false);
  isCapturing = signal(false);
  isSubmitting = signal(false);

  screenshotDataUrl = signal<string>('');
  description = signal('');
  ccEmail = signal('');
  extraFiles = signal<File[]>([]);

  @ViewChild('fileInput', { static: false }) fileInput?: ElementRef<HTMLInputElement>;

  async openDialog() {
    this.isOpen.set(true);
    this.isCapturing.set(true);
    this.description.set('');
    this.ccEmail.set('');
    this.extraFiles.set([]);
    
    try {
      // Small delay to let the dialog render out of the way, or we just capture the whole body
      setTimeout(async () => {
        const canvas = await html2canvas(document.body, {
            ignoreElements: (el) => {
                // Ignore the bug report dialog itself during capture if it's visible
                return el.classList.contains('bug-report-dialog-overlay') || el.classList.contains('bug-fab');
            }
        });
        this.screenshotDataUrl.set(canvas.toDataURL('image/png'));
        this.isCapturing.set(false);
      }, 100);
    } catch (e) {
      this.toast.error('Failed to capture screenshot.');
      this.isCapturing.set(false);
    }
  }

  closeDialog() {
    this.isOpen.set(false);
  }

  triggerFileInput() {
    this.fileInput?.nativeElement.click();
  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files) {
      const filesArray = Array.from(input.files);
      this.extraFiles.update(files => [...files, ...filesArray]);
    }
  }

  removeFile(index: number) {
    this.extraFiles.update(files => {
      const newFiles = [...files];
      newFiles.splice(index, 1);
      return newFiles;
    });
  }

  async submitReport() {
    if (!this.description().trim()) {
      this.toast.error('Please enter a description.');
      return;
    }

    this.isSubmitting.set(true);
    const formData = new FormData();
    formData.append('description', this.description());
    formData.append('ccEmail', this.ccEmail());
    formData.append('screenshot', this.screenshotDataUrl());

    this.extraFiles().forEach((file, idx) => {
      formData.append(`extra-${idx}`, file, file.name);
    });

    try {
      await this.http.post('/v1/bugs', formData).toPromise();
      this.toast.success('Bug report sent successfully.');
      this.closeDialog();
    } catch (e) {
      this.toast.error('Failed to send bug report.');
    } finally {
      this.isSubmitting.set(false);
    }
  }
}
