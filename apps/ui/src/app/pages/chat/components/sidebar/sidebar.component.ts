import { Component, EventEmitter, Input, Output, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { AuthService } from '../../../../services/auth.service';
import { Conversation } from '../../../../services/chat-api.service';

@Component({
  selector: 'app-chat-sidebar',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.css'
})
export class SidebarComponent {
  public readonly auth = inject(AuthService);

  @Input() history: Conversation[] = [];
  @Input() conversationId = '';
  @Input() selectedModel = 'aether-2.0';

  @Output() newChat = new EventEmitter<void>();
  @Output() loadConversation = new EventEmitter<string>();
  @Output() deleteConversation = new EventEmitter<string>();
  @Output() logout = new EventEmitter<void>();
}
