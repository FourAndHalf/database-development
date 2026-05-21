import { CommonModule } from '@angular/common';
import { Component, signal, effect, computed, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ChatApiService, Conversation } from '../../services/chat-api.service';
import { AuthService } from '../../services/auth.service';
import { ToastService } from '../../services/toast.service';
import { firstValueFrom } from 'rxjs';

@Component({
  standalone: true,
  selector: 'app-explore-page',
  imports: [CommonModule, FormsModule, RouterModule],
    templateUrl: './explore-page.component.html',
  styleUrl: './explore-page.component.css'
})
export class ExplorePageComponent {
  private readonly api = inject(ChatApiService);
  private readonly auth = inject(AuthService);
  private readonly toast = inject(ToastService);
  
  query = signal('');
  results = signal<any[]>([]);
  busyDelete = signal<string | null>(null);

  showUpload = false;
  uploading = false;
  upData = {
    title: '',
    authors: '',
    tags: '',
    file: null as File | null
  };

  constructor() {
    this.search();
  }

  isAdmin(): boolean {
    const user = this.auth.user();
    return !!user && user.type_id === 2;
  }

  async search() {
    try {
      const res = await firstValueFrom(this.api.searchPapers(this.query()));
      this.results.set(res || []);
    } catch (err) {
      console.error('Failed to search papers:', err);
    }
  }

  async deletePaper(id: string, title: string) {
    if (!confirm(`Are you sure you want to permanently delete "${title}"? This will remove it from the SQL database and purge its vectors from ChromaDB.`)) {
      return;
    }
    this.busyDelete.set(id);
    try {
      await firstValueFrom(this.api.deletePaper(id));
      await this.search();
      this.toast.success(`Successfully deleted "${title}"`);
    } catch (err) {
      console.error('Failed to delete paper:', err);
      this.toast.error('Failed to delete paper. Are you an admin?');
    } finally {
      this.busyDelete.set(null);
    }
  }

  onFileSelected(event: any) {
    const file = event.target.files[0];
    if (file) {
      this.upData.file = file;
    }
  }

  async upload() {
    if (!this.upData.file) return;
    this.uploading = true;
    try {
      const formData = new FormData();
      formData.append('file', this.upData.file);
      formData.append('title', this.upData.title);
      formData.append('authors', this.upData.authors);
      formData.append('tags', this.upData.tags);
      
      await firstValueFrom(this.api.uploadPaper(formData));
      
      this.showUpload = false;
      this.upData = { title: '', authors: '', tags: '', file: null };
      await this.search();
      this.toast.success('Paper uploaded successfully! It is now stored in data/raw_pdfs.');
    } catch (err) {
      console.error('Upload failed:', err);
      this.toast.error('Failed to upload paper. Please ensure the file is valid.');
    } finally {
      this.uploading = false;
    }
  }

  getViewerUrl(filename: string): string {
    return `/pdfs/${filename}`;
  }
}
