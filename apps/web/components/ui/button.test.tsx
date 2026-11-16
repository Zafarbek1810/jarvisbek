import React from 'react';
import {it,expect} from 'vitest';
import {render,fireEvent} from '@testing-library/react';
import {Button} from './button';
it('amalni foydalanuvchi bosganda bajaradi',()=>{let clicks=0;const view=render(<Button onClick={()=>clicks++}>Saqlash</Button>);fireEvent.click(view.getByRole('button',{name:'Saqlash'}));expect(clicks).toBe(1);});
