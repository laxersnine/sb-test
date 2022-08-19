import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';
import { MatInputModule } from '@angular/material/input';
import { MatTableModule } from '@angular/material/table';
import { MatSortModule } from '@angular/material/sort';
import { MatGridListModule } from '@angular/material/grid-list';
import { MatButtonModule } from '@angular/material/button';


import { UserRoutingModule } from './user-routing.module';
import { IndexComponent } from './index/index.component';
import { DataTableComponent } from './components/data-table/data-table.component';
import { UserService } from '../services/user.service';


@NgModule({
  declarations: [
    IndexComponent,
    DataTableComponent
  ],
  imports: [
    CommonModule,
    FormsModule,
    HttpClientModule,
    MatInputModule,
    MatTableModule,
    MatButtonModule,
    MatSortModule,
    MatGridListModule,
    UserRoutingModule
  ],
  providers: [
    UserService
  ]
})
export class UserModule { }
