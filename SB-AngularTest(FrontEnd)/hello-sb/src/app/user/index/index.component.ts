import { Component, OnInit } from '@angular/core';
import { UserService } from 'src/app/services/user.service';
import { User } from '../models/user';
import { Observable } from 'rxjs';

@Component({
  selector: 'user-index',
  templateUrl: './index.component.html',
  styleUrls: ['./index.component.css']
})
export class IndexComponent implements OnInit {
  users$: Observable<User[]>;
  
  constructor(private userService: UserService) {
    this.users$ = this.userService.getUsers();
   }

  ngOnInit(): void {
  }
}
