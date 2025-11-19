/**
 * Auth Token Service
 * Manages authentication token for ADK Web UI
 * Extracts token from URL parameters and provides it to HTTP interceptor
 */

import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class AuthTokenService {
  private tokenSubject: BehaviorSubject<string | null> = new BehaviorSubject<string | null>(null);
  public token$: Observable<string | null> = this.tokenSubject.asObservable();

  constructor() {
    // Try to load token from URL parameters on initialization
    this.loadTokenFromUrl();
  }

  /**
   * Load token from URL query parameters
   */
  private loadTokenFromUrl(): void {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');
    
    if (token) {
      this.setToken(token);
      console.log('[ADK Auth] Token loaded from URL');
      
      // Remove token from URL for security (optional)
      this.removeTokenFromUrl();
    } else {
      console.warn('[ADK Auth] No token found in URL. API requests will fail.');
    }
  }

  /**
   * Remove token from URL after loading it
   */
  private removeTokenFromUrl(): void {
    const url = new URL(window.location.href);
    if (url.searchParams.has('token')) {
      url.searchParams.delete('token');
      window.history.replaceState({}, document.title, url.toString());
    }
  }

  /**
   * Set authentication token
   */
  public setToken(token: string): void {
    this.tokenSubject.next(token);
  }

  /**
   * Get current authentication token
   */
  public getToken(): string | null {
    return this.tokenSubject.value;
  }

  /**
   * Clear authentication token
   */
  public clearToken(): void {
    this.tokenSubject.next(null);
  }

  /**
   * Check if token is available
   */
  public hasToken(): boolean {
    return !!this.tokenSubject.value;
  }
}

