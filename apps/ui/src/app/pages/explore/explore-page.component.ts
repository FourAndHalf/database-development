import { CommonModule } from '@angular/common';
import { Component, signal, effect, computed, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ChatApiService, Conversation } from '../../services/chat-api.service';
import { firstValueFrom } from 'rxjs';

@Component({
  standalone: true,
  selector: 'app-explore-page',
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div class="explore-container">
      <header class="explore-header">
        <div class="header-left">
          <button class="back-btn" routerLink="/chat">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
          </button>
          <h1>Research Repository</h1>
        </div>
        <div class="search-box">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <input 
            type="text" 
            placeholder="Search papers by title, author, or keywords..." 
            [ngModel]="query()" 
            (ngModelChange)="query.set($event); search()"
          >
        </div>
      </header>

      <main class="explore-content">
        <div class="filters">
          <span class="results-count">{{ results().length }} papers found</span>
          <div class="filter-group">
            <!-- Future filters like date or author dropdowns -->
          </div>
        </div>

        <div class="paper-grid">
          @for (p of results(); track p.id) {
            <div class="paper-card">
              <div class="p-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
              </div>
              <div class="p-details">
                <h3 class="p-title">{{ p.title }}</h3>
                <div class="p-authors" *ngIf="p.authors?.length">
                  @for (a of p.authors; track a.id) {
                    <span>{{ a.name }}{{ !$last ? ', ' : '' }}</span>
                  }
                </div>
                <div class="p-meta">
                  <span class="p-filename">{{ p.filename }}</span>
                  <span class="p-date">{{ p.created_at | date:'mediumDate' }}</span>
                </div>
              </div>
              <div class="p-actions">
                <a class="view-pdf-btn" [href]="getViewerUrl(p.filename)" target="_blank">
                  Open PDF
                </a>
                <button class="synth-btn" [routerLink]="['/chat']" [queryParams]="{ q: 'Summarize ' + p.title }">
                  Synthesize
                </button>
              </div>
            </div>
          } @empty {
            <div class="no-results">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="16" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
              <p>No research papers match your search criteria.</p>
            </div>
          }
        </div>
      </main>
    </div>
  `,
  styleUrl: './explore-page.component.css'
})
export class ExplorePageComponent {
  private readonly api = inject(ChatApiService);
  
  query = signal('');
  results = signal<any[]>([]);

  constructor() {
    this.search();
  }

  async search() {
    try {
      const res = await firstValueFrom(this.api.searchPapers(this.query()));
      this.results.set(res || []);
    } catch (err) {
      console.error('Failed to search papers:', err);
    }
  }

  getViewerUrl(filename: string): string {
    // Assuming the API proxies /pdfs/ to the python service static mount
    return `/pdfs/${filename}`;
  }
}
